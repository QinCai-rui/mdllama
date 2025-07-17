"""Release utilities for mdllama: check for new stable and pre-releases on GitHub."""
import sys
import requests
from .version import __version__

def check_github_release():
    """Check for new stable and pre-releases on GitHub and alert the user."""
    import os
    repo = "QinCai-rui/mdllama"
    api_url = f"https://api.github.com/repos/{repo}/releases"
    headers = {}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        resp = requests.get(api_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"Failed to fetch releases from GitHub (status {resp.status_code})")
            if resp.status_code == 403:
                print("Your IP may be rate limited by GitHub. Set a GITHUB_TOKEN environment variable for higher limits.")
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
        import re
        def ver(rel):
            return rel["tag_name"].lstrip("v") if rel else None
        def is_date_version(v):
            return bool(re.match(r"^\d{8}\.\d+$", v))
        def semver_tuple(v):
            return tuple(map(int, (v.split(".") + [0,0,0])[:3]))
        def print_release(rel, kind):
            if rel:
                print(f"Latest {kind} release: {rel['tag_name']} - {rel['html_url']}")
        print(f"Current version: {current}")
        updated = False
        stable_ver = ver(latest_stable)
        pre_ver = ver(latest_prerelease)
        # Only alert for stable if it's truly newer
        if latest_stable and stable_ver != current:
            from datetime import datetime
            def get_published_at(rel):
                return rel.get("published_at")
            if is_date_version(current):
                if stable_ver and is_date_version(stable_ver):
                    # Both are date-based, compare as floats
                    try:
                        if float(stable_ver) > float(current):
                            print("\033[93mA new stable release is available!\033[0m")
                            print_release(latest_stable, "stable")
                            updated = True
                    except Exception:
                        pass
                else:
                    # Current is date-based, stable is semver: compare published_at
                    # Find the current release object
                    current_rel = None
                    for rel in releases:
                        if ver(rel) == current:
                            current_rel = rel
                            break
                    if current_rel and get_published_at(latest_stable) and get_published_at(current_rel):
                        try:
                            stable_time = datetime.fromisoformat(get_published_at(latest_stable).replace('Z', '+00:00'))
                            current_time = datetime.fromisoformat(get_published_at(current_rel).replace('Z', '+00:00'))
                            if stable_time > current_time:
                                print("\033[93mA new stable release is available!\033[0m")
                                print_release(latest_stable, "stable")
                                updated = True
                        except Exception:
                            pass
            else:
                # Current is semver, compare tuples
                if stable_ver and semver_tuple(stable_ver) > semver_tuple(current):
                    print("\033[93mA new stable release is available!\033[0m")
                    print_release(latest_stable, "stable")
                    updated = True
        # Pre-release alert: only if pre-release is newer than current
        if latest_prerelease:
            from datetime import datetime
            def get_published_at(rel):
                return rel.get("published_at")
            if is_date_version(current) and is_date_version(pre_ver):
                # Compare publish dates
                current_rel = None
                for rel in releases:
                    if ver(rel) == current:
                        current_rel = rel
                        break
                if current_rel and get_published_at(latest_prerelease) and get_published_at(current_rel):
                    try:
                        pre_time = datetime.fromisoformat(get_published_at(latest_prerelease).replace('Z', '+00:00'))
                        current_time = datetime.fromisoformat(get_published_at(current_rel).replace('Z', '+00:00'))
                        if pre_time > current_time:
                            print("\033[96mA new pre-release is available!\033[0m")
                            print_release(latest_prerelease, "pre-release")
                            updated = True
                    except Exception:
                        pass
            else:
                # For semver or mixed, just compare version string as before
                if pre_ver != current:
                    print("\033[96mA new pre-release is available!\033[0m")
                    print_release(latest_prerelease, "pre-release")
                    updated = True
        if not updated:
            print("You are using the latest version.")
    except Exception as e:
        print(f"Error checking releases: {e}")
        sys.exit(1)
