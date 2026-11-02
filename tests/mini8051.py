"""Minimal 8051 instruction interpreter extracted from the GM610 v1.4 offline tests.
This is NOT a whole-device emulator.
"""
class Mini8051:
    def __init__(self,rom:bytes):
        self.rom=rom;self.m=bytearray(256);self.x=bytearray(0x10000);self.upper=bytearray(128)
        self.m[0x81]=0x7b
        self.pc=0
    def stack_store(self,addr,v):
        if addr<128:self.m[addr]=v
        else:self.upper[addr-128]=v
    def stack_read(self,addr):
        return self.m[addr] if addr<128 else self.upper[addr-128]
    def val(self,a):return self.m[a]
    def put(self,a,v):self.m[a]=v&255
    def dptr(self):return self.m[0x83]*256+self.m[0x82]
    def setdptr(self,v):self.m[0x83]=v>>8;self.m[0x82]=v&255
    def c(self):return bool(self.m[0xd0]&128)
    def setc(self,v):self.m[0xd0]=(self.m[0xd0]&0x7f)|(128 if v else 0)
    def a(self):return self.m[0xe0]
    def seta(self,n):self.m[0xe0]=n&255
    def r7addr(self):return 7+8*((self.m[0xd0]>>3)&3)
    def op(self):
        p=self.pc; op=self.rom[p];pc=p+1;rm=self.m
        def rel(off):return (pc+off-256 if off>127 else pc+off)&65535
        if op==0xc0: # push direct
            src=self.rom[pc];pc+=1;rm[0x81]=(rm[0x81]+1)&255;self.stack_store(rm[0x81],rm[src])
        elif op==0xd0: # pop direct
            dest=self.rom[pc];pc+=1;rm[dest]=self.stack_read(rm[0x81]);rm[0x81]=(rm[0x81]-1)&255
        elif op==0x53: # AND direct,immediate
            dest,imm=self.rom[pc:pc+2];pc+=2;rm[dest]&=imm
        elif op==0x30: # JNB bit,rel
            bit=self.rom[pc];off=self.rom[pc+1];pc+=2
            addr=0x20+(bit>>3) if bit<128 else bit&0xf8
            if not rm[addr]&(1<<(bit&7)):pc=rel(off)
        elif op==0x60: # JZ
            off=self.rom[pc];pc+=1
            if not self.a():pc=rel(off)
        elif op==0x70: # JNZ
            off=self.rom[pc];pc+=1
            if self.a():pc=rel(off)
        elif op==0x40: # JC
            off=self.rom[pc];pc+=1
            if self.c():pc=rel(off)
        elif op==0x50: # JNC
            off=self.rom[pc];pc+=1
            if not self.c():pc=rel(off)
        elif op==0x80: # SJMP
            off=self.rom[pc];pc+=1;pc=rel(off)
        elif op==0xb4: # CJNE A,#data,rel
            imm,off=self.rom[pc:pc+2];pc+=2;self.setc(self.a()<imm)
            if self.a()!=imm:pc=rel(off)
        elif op==0x90:
            self.setdptr(int.from_bytes(self.rom[pc:pc+2],'big'));pc+=2
        elif op==0x12: # LCALL (not used for LED hook tests)
            target=int.from_bytes(self.rom[pc:pc+2],'big');pc+=2
            rm[0x81]+=1;self.stack_store(rm[0x81],pc&255);rm[0x81]+=1;self.stack_store(rm[0x81],pc>>8);pc=target
        elif op==0x22: # RET
            high=self.stack_read(rm[0x81]);rm[0x81]-=1;low=self.stack_read(rm[0x81]);rm[0x81]-=1;pc=(high<<8)|low
        elif op==0x02:pc=int.from_bytes(self.rom[pc:pc+2],'big')
        elif op==0xe5:self.seta(rm[self.rom[pc]]);pc+=1
        elif op==0xf5:rm[self.rom[pc]]=self.a();pc+=1
        elif op==0x85:
            src,dst=self.rom[pc:pc+2];pc+=2;rm[dst]=rm[src]
        elif op==0x74:self.seta(self.rom[pc]);pc+=1
        elif op==0xe4:self.seta(0)
        elif op==0xf0:self.x[self.dptr()]=self.a()
        elif op==0xe0:self.seta(self.x[self.dptr()])
        elif op==0x54:self.seta(self.a()&self.rom[pc]);pc+=1
        elif op==0x93:self.seta(self.rom[(self.dptr()+self.a())&65535])
        elif op==0x94:
            n=self.rom[pc]+int(self.c());pc+=1;old=self.a();self.seta(old-n);self.setc(old<n)
        elif op==0x9f:
            n=rm[self.r7addr()]+int(self.c());old=self.a();self.seta(old-n);self.setc(old<n)
        elif op==0xc3:self.setc(False)
        elif op==0xff:rm[self.r7addr()]=self.a()
        elif op==0xa4:
            product=self.a()*rm[0xf0];self.seta(product&255);rm[0xf0]=product>>8;self.setc(False)
        elif op==0x14:self.seta(self.a()-1)
        elif op==0x24:self.seta(self.a()+self.rom[pc]);pc+=1 # ADD A,#imm (row offset)
        elif op==0xf8:rm[0+8*((rm[0xd0]>>3)&3)]=self.a() # MOV R0,A
        elif op==0xa3:self.setdptr((self.dptr()+1)&0xffff) # INC DPTR
        elif op==0x56:
            r0=rm[0+8*((rm[0xd0]>>3)&3)];self.seta(self.a()&rm[r0]) # ANL A,@R0
        else:raise AssertionError(f'Unsupported instruction {op:02X} at {p:04X}')
        self.pc=pc
    def run_until(self,stop,steps=250):
        for _ in range(steps):
            if self.pc==stop:return
            self.op()
        raise AssertionError(f'Did not reach {stop:04X}, at {self.pc:04X}')
