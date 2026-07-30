#!/usr/bin/env python3
"""FengMail Universal Setup Tool — install, export, import

Auto-detects OS/architecture, downloads ortie binary, creates directory structure.
Also handles exporting/importing all configs for machine-to-machine migration.

Usage:
  python setup.py                          # Install on new machine (auto-detect OS)
  python setup.py --export                 # Export all configs to portable JSON
  python setup.py --export -o my-bundle    # Export to custom filename
  python setup.py --import <file>          # Restore config from exported bundle
"""
import json, os, platform, shutil, stat, subprocess, sys, tarfile, urllib.request, zipfile

REPO = "https://github.com/pimalaya/ortie/releases/download/v1.1.0"

# (sysname, machine) → (filename, archive_format)
ORTIE_FILES = {
    ("darwin", "arm64"):  ("ortie.aarch64-darwin.tgz", "tgz"),
    ("darwin", "x86_64"): ("ortie.x86_64-darwin.tgz", "tgz"),
    ("win32", "AMD64"):   ("ortie.x86_64-windows.zip", "zip"),
    ("linux", "x86_64"):  ("ortie.x86_64-linux.tgz", "tgz"),
    ("linux", "aarch64"): ("ortie.aarch64-linux.tgz", "tgz"),
}

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(HOME, ".config", "ortie")
TOKENS_DIR = os.path.join(CONFIG_DIR, "tokens")


def system_key():
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    # Windows → win32 (ortie release naming)
    if sysname == "windows":
        sysname = "win32"
    return sysname, machine


def download(url, dest, desc):
    print(f"  ↓ Downloading {desc}...")
    urllib.request.urlretrieve(url, dest)


def unpack(path):
    if path.endswith(".tgz"):
        with tarfile.open(path, "r:gz") as t:
            t.extractall("/usr/local/bin/" if os.name != "nt" else HERE)
    elif path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            z.extractall(HERE)
    bin_name = "ortie" + (".exe" if os.name == "nt" else "")
    bin_path = os.path.join("/usr/local/bin" if os.name != "nt" else HERE, bin_name)
    if os.path.exists(bin_path):
        os.chmod(bin_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH)
        print(f"  ✓ ortie → {bin_path}")
        return bin_path
    print(f"  ⚠  Could not find expected binary: {bin_path}")
    return None


# ── Install ────────────────────────────────────────────────────────────────

def do_setup():
    print(f"=== FengMail Setup ({platform.system()} {platform.machine()}) ===\n")

    key = system_key()
    if key not in ORTIE_FILES:
        print(f"❌ Unsupported platform: {key}")
        sys.exit(1)
    fname, fmt = ORTIE_FILES[key]
    url = f"{REPO}/{fname}"
    tmp = os.path.join(HERE, fname)
    download(url, tmp, f"ortie ({fmt})")
    unpack(tmp)
    os.remove(tmp)

    os.makedirs(TOKENS_DIR, exist_ok=True)
    print(f"  ✓ {TOKENS_DIR}")

    sample = os.path.join(HERE, "accounts.sample.json")
    acct = os.path.join(HERE, "accounts.json")
    if not os.path.exists(acct) and os.path.exists(sample):
        shutil.copy(sample, acct)
        print("  ✓ Created accounts.json from sample (edit before use)")

    print(f"\n✅ Setup complete")
    arch = platform.machine()
    print(f"   Run: python setup.py --import <bundle>  to restore config")
    print(f"   Or:  python setup.py --export           to bundle current setup\n")


# ── Export ─────────────────────────────────────────────────────────────────

def do_export(output):
    acct_path = os.path.join(HERE, "accounts.json")
    if not os.path.exists(acct_path):
        print("❌ accounts.json not found in project directory")
        sys.exit(1)
    with open(acct_path) as f:
        accounts = json.load(f)

    cfg_path = os.path.join(CONFIG_DIR, "config.toml")
    if not os.path.exists(cfg_path):
        print(f"❌ Config not found: {cfg_path}")
        sys.exit(1)
    with open(cfg_path) as f:
        config_toml = f.read()

    if not os.path.exists(TOKENS_DIR):
        print(f"❌ Tokens not found: {TOKENS_DIR}")
        sys.exit(1)
    tokens = {}
    for name in os.listdir(TOKENS_DIR):
        if name.endswith(".txt"):
            p = os.path.join(TOKENS_DIR, name)
            with open(p) as f:
                tokens[name.replace(".txt", "")] = json.load(f)

    bundle = {
        "version": 1,
        "accounts": accounts,
        "config_toml": config_toml,
        "tokens": tokens,
    }
    with open(output, "w") as f:
        json.dump(bundle, f, indent=2)
    print(f"✅ Exported: {output}")
    print(f"   Accounts: {len(accounts)}")
    print(f"   Tokens:   {len(tokens)}")


# ── Import ─────────────────────────────────────────────────────────────────

def do_import(bundle_path):
    if not os.path.exists(bundle_path):
        print(f"❌ Bundle not found: {bundle_path}")
        sys.exit(1)
    with open(bundle_path) as f:
        bundle = json.load(f)

    os.makedirs(TOKENS_DIR, exist_ok=True)

    # accounts.json
    dst = os.path.join(HERE, "accounts.json")
    with open(dst, "w") as f:
        json.dump(bundle["accounts"], f, indent=2)
    print(f"  ✓ accounts.json ({len(bundle['accounts'])} accounts)")

    # tokens
    for name, data in bundle["tokens"].items():
        path = os.path.join(TOKENS_DIR, f"{name}.txt")
        with open(path, "w") as f:
            json.dump(data, f)
        print(f"  ✓ tokens/{name}.txt")
    print(f"  ✓ {len(bundle['tokens'])} tokens restored")

    # config.toml — rewrite paths to current machine
    toml = bundle["config_toml"]
    import re
    old_home_pattern = re.compile(
        r'(?:[Cc]:\\[Uu]sers\\[^\\]+|/[Uu]sers/[^/]+|/home/[^/]+)'
    )
    new_home = HOME.replace("\\", "/")
    toml_normalized = toml.replace("\\\\", "/").replace("\\", "/")
    toml_fixed = old_home_pattern.sub(new_home, toml_normalized)

    dst_cfg = os.path.join(CONFIG_DIR, "config.toml")
    with open(dst_cfg, "w") as f:
        f.write(toml_fixed)
    print(f"  ✓ config.toml (paths rewritten to {platform.system()})")

    print(f"\n✅ Config restored!")
    print(f"   python fengmail.py list-accounts")


# ── Main ───────────────────────────────────────────────────────────────────

def usage():
    print(__doc__)
    sys.exit(1)


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        do_setup()
    elif args[0] == "--export":
        output = "fengmail-config.json"
        if len(args) >= 3 and args[1] == "-o":
            output = args[2]
        do_export(output)
    elif args[0] == "--import":
        if len(args) < 2:
            usage()
        do_import(args[1])
    else:
        usage()
