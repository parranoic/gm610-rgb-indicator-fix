#!/usr/bin/env python3
"""Byte-exact, offline GM610 battery-overlay injection for ONE tested firmware revision.

This is reconstructed 8051 machine code, not vendor source code. These routines
are inserted only into the verified v1.1 Fn->Enter application image. Both the
input and final output are checked against SHA-256 hashes from the owner's unit.
No USB interaction, download, or flashing is performed here.
"""
from __future__ import annotations
import hashlib

APP_SIZE = 0xF000
V11_HASH = "314e2292fb083533b82cecd824f37d087e3a1d259f1fa39859a828b202bdf583"
V12_HASH = "e8d9991bbc20bc7dff46ecb6d80c74c84b28c004ba777adc1fd6d74ed04da712"
FRAME_COUNT = 120  # 120 LED refreshes, not guaranteed to be exactly two seconds
B_MATRIX = 34      # linear scan index, confirmed via the installed firmware scan loop
NUMBER_LED_START = 0x16
NUMBER_LED_END = 0x1F
LEVEL_TO_BARS = [0,2,2,2,4,4,6,8,8,10,10,10,10,10,10,10]

class ASM:
    def __init__(self, start):
        self.start=start;self.b=bytearray();self.labels={};self.fixups=[]
    def here(self):return self.start+len(self.b)
    def label(self,n):
        assert n not in self.labels,n
        self.labels[n]=self.here()
    def op(self,*data):self.b.extend(data)
    def rel(self,opcode,*pre,label):
        self.op(opcode,*pre,0);self.fixups.append(('rel',len(self.b)-1,label))
    def abs(self,opcode,label):
        self.op(opcode,0,0);self.fixups.append(('abs',len(self.b)-2,label))
    def assemble(self):
        for kind, i, name in self.fixups:
            addr=self.labels[name]
            if kind=='rel':
                d=addr-(self.start+i+1)
                if not -128<=d<=127:raise ValueError(f'Branch {name} out of range: {d}')
                self.b[i]=d&255
            else:self.b[i:i+2]=addr.to_bytes(2,'big')
        return bytes(self.b)

def key_hook():
    a=ASM(0x9000)
    # At 0x618F the scan loop sets 08h=0. Then it walks 21 rows × 6 columns,
    # incrementing 08h once for EVERY tested key at 0x61BA. B is table index
    # 34 (row 5, col 4), confirmed by HID usage 0x05 at C600+4*34+2.
    # No proxy row/column variables: use the exact index passed to 0x0DC0.
    a.op(0xc0,0xd0)          # PUSH PSW (CJNE sets Carry)
    a.op(0xc0,0xe0)          # PUSH ACC (original displaced MOV DPTR did not touch A)
    a.rel(0x30,0x33,label='done')   # JNB Fn-held bit 33h
    a.op(0xe5,0x08)          # MOV A,08h: linear matrix scan index (0..125)
    a.rel(0xb4,B_MATRIX,label='done') # only key index 34: B
    a.op(0x90,0x0e,0x30)    # MOV DPTR,#0E30h
    a.op(0x74,FRAME_COUNT)   # MOV A,#frames
    a.op(0xf0)              # MOVX @DPTR,A
    a.label('done')
    a.op(0xd0,0xe0)          # POP ACC
    a.op(0xd0,0xd0)          # POP PSW
    a.op(0x90,0x0d,0xd0)    # displaced MOV DPTR,#0DD0h
    a.op(0x22)              # RET
    return a.assemble()

def init_hook():
    a=ASM(0x9020)
    a.op(0x12,0x7c,0x3f)   # original LCALL 7C3Fh
    a.op(0x90,0x0e,0x30)   # timer at XDATA 0E30h
    a.op(0xe4,0xf0)        # clear A; MOVX @DPTR,A
    a.op(0x22)
    return a.assemble()

def led_hook():
    a=ASM(0x9040)
    for s in [0xd0,0xe0,0xf0,0x82,0x83,0x07]:a.op(0xc0,s) # PUSH PSW,ACC,B,DPL,DPH,R7(bank0)
    a.op(0x53,0xd0,0xe7)    # ANL PSW,#E7h: temporarily force register bank 0 for R7 scratch
    a.op(0x90,0x0e,0x30,0xe0)  # read active timer
    a.rel(0x60,label='finish')   # JZ -> normal rendering
    a.op(0xe5,0x15,0xc3,0x94,0x16)  # A=LED index - 22
    a.rel(0x40,label='finish')   # before number row
    a.op(0xff)                    # MOV R7,A (number slot)
    a.op(0xc3,0x94,0x0a)          # compare slot <10
    a.rel(0x50,label='finish')   # after number row
    a.op(0x90,0x0e,0x05,0xe0,0x54,0x0f) # battery 4-bit status
    a.abs(0x90,'levels')
    a.op(0x93)                   # MOVC A,@A+DPTR (0-10 bars)
    a.rel(0x60,label='tick')     # Unknown/zero: no override (wired behavior)
    a.op(0xc3,0x9f)              # A=bars-R7
    a.rel(0x40,label='off')      # if bars < slot
    a.rel(0x60,label='off')      # if bars == slot
    a.op(0xe5,0x16)              # channel 0 red, 1 green, 2 blue
    a.rel(0xb4,0x01,label='off') # only green ON
    a.op(0x74,0xff)              # maximum 8-bit green
    a.op(0x85,0x19,0xf0,0xa4)   # B=global brightness; MUL AB
    a.op(0x85,0xf0,0x12,0xf5,0x13) # 16-bit PWM duty high/low
    a.rel(0x80,label='tick')
    a.label('empty')
    a.op(0xe5,0x07)              # MOV A,07h: saved slot is in bank 0 R7
    a.rel(0x70,label='off')      # Only slot 0
    a.op(0xe5,0x16)              # channel: red=0
    a.rel(0x70,label='off')
    a.op(0x74,0xff)              # maximum red
    a.op(0x85,0x19,0xf0,0xa4)   # B=global brightness; MUL AB
    a.op(0x85,0xf0,0x12,0xf5,0x13)
    a.rel(0x80,label='tick')
    a.label('off')
    a.op(0xe4,0xf5,0x12,0xf5,0x13) # duty=0 (off)
    a.label('tick')
    a.op(0xe5,0x15)               # current LED
    a.rel(0xb4,0x16,label='finish') # only once per scan cycle on key 1
    a.op(0xe5,0x16)
    a.rel(0x70,label='finish')     # only channel 0
    a.op(0x90,0x0e,0x30,0xe0,0x14,0xf0) # timer--
    a.label('finish')
    for s in [0x07,0x83,0x82,0xf0,0xe0,0xd0]:a.op(0xd0,s)
    # Displaced instructions at 0x4E88..4E8C. CJNE rel=0 sets Carry
    # exactly as before and continues at 0x4E8D.
    a.op(0xe5,0x14,0xb4,0x15,0x00,0x02,0x4e,0x8d)
    a.label('levels')
    a.op(*LEVEL_TO_BARS)
    return a.assemble()



def inject_battery_overlay(v11: bytes) -> tuple[bytes, tuple[int, ...]]:
    """Create the hardware-tested v1.2 battery overlay from the verified v1.1 image."""
    if len(v11) != APP_SIZE or hashlib.sha256(v11).hexdigest() != V11_HASH:
        raise ValueError("Expected the exact tested v1.1 Fn->Enter application; refusing to inject")
    image = bytearray(v11)

    def replace(offset: int, original: bytes, changed: bytes, description: str) -> None:
        if len(original) != len(changed) or image[offset:offset+len(original)] != original:
            raise ValueError(f"Unexpected bytes at 0x{offset:04X} for {description}")
        image[offset:offset+len(changed)] = changed

    # Existing key-scan path: original MOV DPTR,#0DD0h is reproduced in key_hook.
    replace(0x0DC0, bytes.fromhex("90 0D D0"), bytes.fromhex("12 90 00"), "Fn+B key hook")
    # Original LCALL 7C3Fh is reproduced in init_hook, then timer is initialized.
    replace(0x8536, bytes.fromhex("12 7C 3F"), bytes.fromhex("12 90 20"), "timer initialization")
    # Original comparison with Carry is reproduced in LED hook before resuming.
    replace(0x4E88, bytes.fromhex("E5 14 B4 15 00"), bytes.fromhex("02 90 40 00 00"), "LED PWM hook")
    for address, blob in ((0x9000, key_hook()), (0x9020, init_hook()), (0x9040, led_hook())):
        if address + len(blob) > APP_SIZE or image[address:address+len(blob)] != b"\x00"*len(blob):
            raise ValueError(f"Nonempty or oversized code cave at 0x{address:04X}")
        image[address:address+len(blob)] = blob
    result = bytes(image)
    result_hash = hashlib.sha256(result).hexdigest()
    if result_hash != V12_HASH:
        raise AssertionError(f"Unexpected v1.2 image hash: {result_hash}")
    changed = tuple(i for i,(a,b) in enumerate(zip(v11,result)) if a != b)
    return result, changed
