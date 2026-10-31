# Publishing on GitHub

Suggested repository name: **`gm610-rgb-indicator-fix`**

Suggested description: **Nine-byte, AI-assisted Newmen GM610 firmware patch that lets Fn and Tab follow normal RGB lighting. Source-only; backup and flashing required.**

Suggested topics: `newmen`, `gm610`, `rgb`, `keyboard`, `sinowealth`, `sh68f90`, `firmware-patch`, `reverse-engineering`, `vibe-coded`

## Before publishing

- Review the README, especially the compatibility hash, safety notice and AI-assisted/vibe-coded disclosure.
- Don't add your private backups or generated firmware. This source-only package contains **no `.bin` or `.exe` files**.
- If you prefer your own copyright name, edit the MIT LICENSE copyright line; **do not** apply that license to the Newmen firmware or `sinowisp`/`hidapitester` binaries.
- Test the generator locally and confirm that your original backup is safe and archived separately.

## Publish via Git

Create an empty GitHub repository (without auto-generating its own README or LICENSE), then run these commands **from the extracted source repository directory**:

```powershell
git init
git branch -M main
git add .
git status --short
# Inspect the staged files before continuing. There should be NO firmware images.
git commit -m "Initial source-only GM610 RGB indicator patch"
git remote add origin https://github.com/YOUR_USERNAME/gm610-rgb-indicator-fix.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. If your Git version does not accept `git branch -M main` immediately after `git init`, run it after the first commit.

### Final check

```powershell
git ls-files
```

Expected: only `.md`, `.py`, `.yml`, `.gitignore`, and `LICENSE` files. **If you see any `.bin`, `.exe`, `.DAT`, `.hex`, backup, updater, or private hardware dump, remove it from the staged files before pushing.** A `.gitignore` protects *untracked* files; it does not automatically remove already-tracked files.

> GitHub's web **Upload files** interface can also work, but you must upload the extracted source files, **not the ZIP as a single file**. Check that hidden `.gitignore` and `.github/workflows/tests.yml` are included.
