# 📦 KuttyPets Distribution & Release Guide

This guide explains how to publish **KuttyPets** on GitHub and share ready-to-run downloads with **Windows**, **macOS**, and **Linux** users.

---

## 🚀 Step 1: Push to GitHub

Initialize your git repository (if not already done) and push to GitHub:

```bash
cd /home/kutty/kuttypets
git init
git add .
git commit -m "feat: initial release of KuttyPets cross-platform companion"

# Link to your GitHub repository
git remote add origin https://github.com/<your-username>/kuttypets.git
git branch -M main
git push -u origin main
```

---

## 🏷️ Step 2: Trigger Automatic Builds for All OSes

Whenever you want to release a new version (e.g. `v1.0.0`), simply create and push a Git tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

### What Happens Automatically in GitHub Actions:
1. **Windows Runner**: Compiles `KuttyPets.exe` and bundles it into `KuttyPets-Windows-x64.zip`.
2. **macOS Runner**: Builds `KuttyPets.app` and bundles it into `KuttyPets-macOS.zip`.
3. **Linux Runner**: Builds the standalone binary into `KuttyPets-Linux-x64.tar.gz`.
4. **Release Publisher**: Automatically publishes a GitHub Release with all download links attached!

---

## 🔗 Step 3: What to Share with Users

Once the GitHub Action completes (~2 minutes), you will have a release page:
`https://github.com/<your-username>/kuttypets/releases/latest`

### Instructions for Windows Users:
> 1. Download **`KuttyPets-Windows-x64.zip`** from the release page.
> 2. Right-click $\to$ **Extract All**.
> 3. Double-click **`KuttyPets.exe`**.
> 4. Spider-Man will immediately appear and crawl across your open windows!

### Instructions for macOS Users:
> 1. Download **`KuttyPets-macOS.zip`**.
> 2. Unzip and drag **`KuttyPets.app`** to your `/Applications` folder.
> 3. Launch from Spotlight or Launchpad.

### Instructions for Linux Users:
> 1. Download **`KuttyPets-Linux-x64.tar.gz`** or clone and run `pip install -e .`.
> 2. Run `kuttypets --character spiderman`.
