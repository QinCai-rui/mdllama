"""Release utilities for mdllama: check for new stable and pre-releases on GitHub."""
import sys
import requests
from .version import __version__

def check_github_release():
    """Check for new stable and pre-releases on GitHub and alert the user."""
    repo = "QinCai-rui/mdllama"
    api_url = f"https://api.github.com/repos/{repo}/releases"
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code != 200:
            print(f"Failed to fetch releases from GitHub (status {resp.status_code})")
            sys.exit(1)
        releases = resp.json()
        if not releases:
            print("No releases found on GitHub.")
            sys.exit(0)
        current = __version__
        latest_stable = None
        latest_prerelease = None
        for rel in releases:
            if not rel.get("prerelease", False) and not latest_stable:
                latest_stable = rel
            if rel.get("prerelease", False) and not latest_prerelease:
                latest_prerelease = rel
            if latest_stable and latest_prerelease:
                break
        def ver(rel):
            return rel["tag_name"].lstrip("v") if rel else None
        def print_release(rel, kind):
            if rel:
                print(f"Latest {kind}: {rel['tag_name']} - {rel['html_url']}")
        print(f"Current version: {current}")
        updated = False
        if latest_stable and ver(latest_stable) != current:
            print("\033[93mA new stable release is available!\033[0m")
            print_release(latest_stable, "stable release")
            updated = True
        if latest_prerelease and ver(latest_prerelease) != current:
            print("\033[96mA new pre-release is available!\033[0m")
            print_release(latest_prerelease, "pre-release")
            updated = True
        if not updated:
            print("You are using the latest version.")
    except Exception as e:
        print(f"Error checking releases: {e}")
        sys.exit(1)
