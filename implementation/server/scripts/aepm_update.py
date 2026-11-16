#!/usr/bin/env python3
"""Update this application to the newest published version of its recipe with aepm, from the repository root.

  python3 components/ourapps-release/server/scripts/aepm_update.py propose --aepm AEPM --work WORK
      Designs the newest recipe version with the answers and substitutions in .aepm/definition.json, proposes the update
      (aepm runs the packages' checks on the staged tree) and writes .aepm/update/definition.json and summary.md for review.
      Writes nothing when the recipe is already at its newest version.
  python3 components/ourapps-release/server/scripts/aepm_update.py apply --aepm AEPM --work WORK --owner-key KEY
      Proposes .aepm/update/definition.json again, approves it with the owner's private key and applies it, then removes
      .aepm/update/.

AEPM is an aepm checkout; WORK an empty folder outside the repository for the package store, policy and proposal. The
policy trusts Level N's release and guardian keys (https://ourapps.app/policy/levelnpolicy.json), the owner key (for propose,
a key made for the run), and the exact packages of the design for running their checks. Needs Python 3.12, Node and git.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import Request, urlopen

STORE_ADDRESS = os.environ.get("AEPM_FROM", "https://ourapps.app")
# The application folder by its path: apply replaces the folder, so the working directory itself is not followed.
APP = Path(os.getcwd())
RECORDS = APP / ".aepm"
UPDATE = RECORDS / "update"


def get(path):
    # The store refuses requests without a client name.
    with urlopen(Request(STORE_ADDRESS + path, headers={"User-Agent": "aepm-update"}), timeout=60) as response:
        return json.loads(response.read())


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def aepm(args, root, capture=False):
    environment = dict(os.environ, PYTHONPATH=str(root))
    print("$ aepm " + " ".join(args), file=sys.stderr, flush=True)
    result = subprocess.run([sys.executable, "-B", "-m", "aepm", *args], env=environment, text=True,
                            stdout=subprocess.PIPE if capture else None)
    if result.returncode:
        sys.exit(f"aepm {args[0]} failed with exit status {result.returncode}")
    return result.stdout


def public_key(private_key):
    script = "process.stdout.write(require('node:crypto').createPublicKey(require('node:fs').readFileSync(process.argv[1])).export({type:'spki',format:'pem'}))"
    return subprocess.run(["node", "-e", script, str(private_key)], check=True, capture_output=True, text=True).stdout


def disposable_key():
    script = "process.stdout.write(require('node:crypto').generateKeyPairSync('ed25519').publicKey.export({type:'spki',format:'pem'}))"
    return subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True).stdout


def policy(work, owner, lock):
    level_n = get("/policy/levelnpolicy.json")
    document = {"format": 1, "keys": {"release": level_n["keys"]["release"], "guardian": level_n["keys"]["guardian"], "owner": owner},
                "trustedExecution": sorted({entry["digest"] for entry in read(lock)["packages"]})}
    write(work / "policy.json", document)
    return work / "policy.json"


def fetch(root, store, definition):
    """The recipe the definition names with every component it names, and each substituted component."""
    recipe = definition["recipe"]
    aepm(["fetch", f"{recipe['name']}@{recipe['version']}", "--with-dependencies", "--store", str(store), "--from", STORE_ADDRESS], root)
    for selection in (definition.get("selections") or {}).values():
        if selection.get("reason") == "substituted":
            aepm(["fetch", f"{selection['component']}@{selection['version']}", "--store", str(store), "--from", STORE_ADDRESS], root)


def restore(root, work, owner):
    """Put back aepm's package copies and archives, which the repository leaves out, by installing the current design again."""
    store = work / "store"
    fetch(root, store, read(RECORDS / "definition.json"))
    current = policy(work, owner, RECORDS / "lock.json")
    target = work / "current"
    aepm(["install", str(RECORDS / "definition.json"), "--lock", str(RECORDS / "lock.json"), "--store", str(store), "--policy", str(current), "--target", str(target)], root)
    for name in ("packages", "archives"):
        if (target / ".aepm" / name).is_dir() and not (RECORDS / name).exists():
            shutil.copytree(target / ".aepm" / name, RECORDS / name, symlinks=True)
    shutil.rmtree(target)
    return store


def design(root, work, store, definition, version):
    """The definition of the recipe at version with the current answers and substitutions."""
    write(work / "answers.json", definition.get("answers") or {})
    recipe = definition["recipe"]["name"]
    substitutes = [f"{slot}={selection['component']}@{selection['version']}"
                   for slot, selection in sorted((definition.get("selections") or {}).items()) if selection.get("reason") == "substituted"]
    aepm(["fetch", f"{recipe}@{version}", "--with-dependencies", "--store", str(store), "--from", STORE_ADDRESS], root)
    command = ["design", f"{recipe}@{version}", "--store", str(store), "--answers", str(work / "answers.json"), "--out", str(work / "next.json")]
    for substitute in substitutes:
        command += ["--substitute", substitute]
    aepm(command, root)
    return work / "next.json"


def propose(root, work, store, next_definition, owner):
    lock = work / "next-lock.json"
    aepm(["resolve", str(next_definition), "--catalogue", str(store / "catalogue.json"), "--out", str(lock)], root)
    trusted = policy(work, owner, lock)
    aepm(["propose-update", str(APP), str(next_definition), "--store", str(store), "--policy", str(trusted), "--trusted", "--allow-network",
          "--out", str(work / "proposal.json")], root)
    return trusted, lock


def newest(name):
    listed = get("/api/recipes")["recipes"]
    return next(entry["version"] for entry in listed if entry["name"] == name)


def output(name, value):
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as handle:
            handle.write(f"{name}={value}\n")
    print(f"{name}={value}")


def command_propose(arguments, root, work):
    current = read(RECORDS / "definition.json")
    name, installed = current["recipe"]["name"], current["recipe"]["version"]
    version = arguments.version or newest(name)
    if version == installed:
        output("version", "")
        print(f"{name} {installed} is the newest version", file=sys.stderr)
        return
    # Nothing is approved here, so a key made for this run stands in for the owner's.
    owner = [{"publicKey": disposable_key()}]
    store = restore(root, work, owner)
    next_definition = design(root, work, store, current, version)
    _, lock = propose(root, work, store, next_definition, owner)
    before = {entry["name"]: entry["version"] for entry in read(RECORDS / "lock.json")["packages"]}
    after = {entry["name"]: entry["version"] for entry in read(lock)["packages"]}
    lines = [f"# {name} {installed} to {version}", "", "aepm staged the update and ran the packages' checks on it.", "",
             "| Package | Installed | Proposed |", "|---|---|---|"]
    for package in sorted(set(before) | set(after)):
        if before.get(package) != after.get(package):
            lines.append(f"| {package} | {before.get(package, '-')} | {after.get(package, '-')} |")
    lines += ["", "Merging this pull request applies the update: the aepm-update workflow approves it with the owner key and commits the result."]
    UPDATE.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(next_definition, UPDATE / "definition.json")
    (UPDATE / "summary.md").write_text("\n".join(lines) + "\n")
    output("version", version)


def command_apply(arguments, root, work):
    if not (UPDATE / "definition.json").is_file():
        sys.exit("no .aepm/update/definition.json to apply")
    owner = [{"publicKey": public_key(arguments.owner_key)}]
    next_definition = work / "next.json"
    shutil.copyfile(UPDATE / "definition.json", next_definition)
    shutil.rmtree(UPDATE)
    store = restore(root, work, owner)
    fetch(root, store, read(next_definition))
    trusted, _ = propose(root, work, store, next_definition, owner)
    aepm(["approve", str(work / "proposal.json"), "--key", str(arguments.owner_key), "--policy", str(trusted), "--out", str(work / "approval.json")], root)
    aepm(["apply", str(APP), str(work / "proposal.json"), "--approval", str(work / "approval.json"), "--policy", str(trusted)], root)
    output("version", read(RECORDS / "definition.json")["recipe"]["version"])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("propose", "apply"))
    parser.add_argument("--aepm", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--version", help="the recipe version to propose (default: the newest published)")
    parser.add_argument("--owner-key", type=Path, help="the owner's private key (apply)")
    arguments = parser.parse_args()
    if not (RECORDS / "definition.json").is_file():
        sys.exit("run from the application repository's root")
    work = arguments.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if arguments.action == "apply" and arguments.owner_key is None:
        sys.exit("apply needs --owner-key")
    (command_propose if arguments.action == "propose" else command_apply)(arguments, arguments.aepm.resolve(), work)


if __name__ == "__main__":
    main()
