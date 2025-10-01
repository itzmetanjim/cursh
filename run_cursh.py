def main():

    import requests
    import colorama
    import argparse
    import os
    import sys
    import json
    import re
    import hashlib
    colorama.init(autoreset=True)
    argv=sys.argv
    parser=argparse.ArgumentParser(description="A safer alternative to curl ... | sh installers.\n Cursh checks the URL against a trusted list before downloading and executing the script.\nIf not found, it uses SHA256 hash, PGP/GPG signature, trusted domain, etc verification methods and prompts the user for confirmation if not confident enough.\nConfig file is stored at ~/.cursh.json")
    parser.add_argument("url", help="The URL of the installer script to download and execute.")
    parser.add_argument("-f", "--force", action="store_true", help="Check for other heuristics even if the URL is not in the trusted list.")
    parser.add_argument("-T", "--trust_source",action="append", help="Path to a local trusted JSON file or an URL to one starting with https://. Can be specified multiple times.")
    parser.add_argument("--no_trust_default", action="store_true", help="Do not use the default trusted JSON URL list.")
    parser.add_argument("-n","--trust_only", action="store_true", help="Automatically abort when confirmation is required to run the script (if its not in the trust list).")
    args=parser.parse_args()
    url=args.url
    force=args.force
    trust_sources=args.trust_source.copy() if args.trust_source else []
    trust_only=args.trust_only
    no_trust_default=args.no_trust_default
    trusted_data = []
    config=dict()
    config_path = os.path.join(os.path.expanduser("~"), "cursh.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        # Create an empty config file if it doesn't exist
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"__comment":"Config for cursh. Available keys: default_trusted_url (string, default https://raw.githubusercontent.com/itzmetanjim/cursh/refs/heads/main/trusted.json), cache (bool, default true), default_custom_sources (list, default []). See https://github.com/itzmetanjim/cursh/wiki"}, f)
    except Exception as e:
        pass # Ignore other errors

    ################ BUILDING TRUST SOURCES ################
    # First, append all the default custom sources from config if any
    if config.get("default_custom_sources"):
        trust_sources.extend(config.get("default_custom_sources", []))

    default_trusted_url = config.get("default_trusted_url", "https://raw.githubusercontent.com/itzmetanjim/cursh/refs/heads/main/trusted.json")
    if not no_trust_default:
        try:
            trustlist = requests.get(default_trusted_url,allow_redirects=True, timeout=10,verify=True)
            with open(os.path.join(os.path.expanduser("~"), "trust_cache.json"), "w", encoding="utf-8") as f:
                f.write(trustlist.text)
            trusted_data.extend(trustlist.json().get("apps", []))
        except Exception as e:
            if isinstance(e, requests.exceptions.SSLError):
                        print(f"""{colorama.Fore.RED}
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    @             WARNING: SSL CERTIFICATE ERROR!             @
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    IT'S POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
    There was an SSL certificate error while trying to fetch the trusted list from the default source.
    Someone could be intercepting your connection, or your source may not support HTTPS.
    For more information, visit: https://github.com/itzmetanjim/cursh/wiki
    {colorama.Style.RESET_ALL}""")
            print(f"{colorama.Fore.YELLOW}WARN: Failed to fetch trusted list from default URL {default_trusted_url}.\n {e}{colorama.Style.RESET_ALL}")
            if config.get("cache", True):
                try:
                    with open(os.path.join(os.path.expanduser("~"), "trust_cache.json"), "r", encoding="utf-8") as f:
                        cached_trustlist = json.load(f)
                        trusted_data.extend(cached_trustlist.get("apps", []))
                        print(f"{colorama.Fore.YELLOW}WARN: Using cached trust list from ~/.trust_cache.json{colorama.Style.RESET_ALL}")
                except Exception as e:
                    print(f"{colorama.Fore.YELLOW}WARN: No cached trust list found at ~/.trust_cache.json. Please check your internet connection or provide a custom trusted JSON file using -T option.{colorama.Style.RESET_ALL}")
                    if not trust_sources and not force:
                        print(f"{colorama.Fore.RED}ERROR: No more trusted sources available. Try cursh --help or see https://github.com/itzmetanjim/cursh/wiki {colorama.Style.RESET_ALL}")
                        sys.exit(1)
            else:
                if not trust_sources and not force:
                    print(f"{colorama.Fore.RED}ERROR: Caching disabled and no more trusted sources available. Try cursh --help or see https://github.com/itzmetanjim/cursh/wiki {colorama.Style.RESET_ALL}")
                    sys.exit(1)
    if trust_sources:
        for source in trust_sources:
            if source.startswith("https://"):
                try:
                    r = requests.get(source,allow_redirects=True, timeout=10,verify=True)
                    r.raise_for_status()
                    trusted_data.extend(r.json().get("apps", []))
                except Exception as e:
                    if isinstance(e, requests.exceptions.SSLError):
                        print(f"""{colorama.Fore.RED}
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    @             WARNING: SSL CERTIFICATE ERROR!             @
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    IT'S POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
    There was an SSL certificate error while trying to fetch the trusted list from {source}.
    Someone could be intercepting your connection, or your source may not support HTTPS.
    For more information, visit: https://github.com/itzmetanjim/cursh/wiki
    {colorama.Style.RESET_ALL}""")
                    print(f"{colorama.Fore.YELLOW}WARN: Failed to fetch remote trusted list from {source}.\n {e}{colorama.Style.RESET_ALL}")
            else:
                try:
                    with open(source, "r", encoding="utf-8") as f:
                        local_trustlist = json.load(f)
                        trusted_data.extend(local_trustlist.get("apps", []))
                except Exception as e:
                    print(f"{colorama.Fore.YELLOW}WARN: Failed to read local trusted list from {source}.\n {e}{colorama.Style.RESET_ALL}")
    #Check if there are any trusted sources available now
    if not trusted_data and not force:
        print(f"{colorama.Fore.RED}ERROR: No more trusted sources available. Try cursh --help or see https://github.com/itzmetanjim/cursh/wiki {colorama.Style.RESET_ALL}")
        sys.exit(1)

    ################ URL CHECK ################

    consistent_responses = True
    sha256sum_pass = False
    pgp_pass = False
    trusted_list_match = False
    trusted_list_version_match = False

    headers =[
        {"User-Agent":"curl/8.16.0"},
        {"User-Agent":"Wget/1.25.0 (linux-gnu)"},
        {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-mobile": '?0'
        }
    ]
    responses=[]
    for i in headers:
        try:
            response = requests.get(url, headers=i, timeout=10, allow_redirects=True, verify=True)
            responses.append(response)
            if response.status_code != 200:
                print(f"{colorama.Fore.YELLOW}WARN: HTTP {response.status_code} for the URL {url} with headers {i['User-Agent'][:41]}.{colorama.Style.RESET_ALL}")

        except Exception as e:
            print(f"{colorama.Fore.YELLOW}WARN: Failed to fetch the URL {url} with headers {i["User-Agent"][:41]}.\n {e}{colorama.Style.RESET_ALL}")

    for i in responses:
        if i.text != responses[0].text:
            print(f"""{colorama.Fore.RED}
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    @             WARNING: INCONSISTENT RESPONSES!            @
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    Responses with the user agent {i.request.headers.get('User-Agent')} and {responses[0].request.headers.get('User-Agent')} are different.
    This could indicate that the server is serving different content based on the user agent, which may be suspicious.
    The server may be trying to serve a malicious script to curl/wget while serving a non malicious script to browsers.
    You should open the script in a web browser. Then, check if it redirects to an HTML page or shows a script.
    If it shows a script, IT'S RECOMMENDED NOT TO RUN IT, as this is NOT the script you will be running with curl/wget.
    For more information, visit: https://github.com/itzmetanjim/cursh/wiki
    {colorama.Style.RESET_ALL}""")
            consistent_responses = False
    script_content = None
    for i in responses:
        if i.status_code == 200:
            script_content = i.text
            break
    with open(os.path.join(os.path.expanduser("~"), "cursh_last_script.sh"), "w", encoding="utf-8") as f:
        if script_content:
            f.write(script_content)
        else:
            print(f"{colorama.Fore.RED}ERROR: Failed to fetch the script from {url}. No valid response received.{colorama.Style.RESET_ALL}")
            sys.exit(1)
    # Check for sha256 sum url
    sha256_url = None
    m = re.search(r"SHA256\s?:\s?(.*)", script_content, re.IGNORECASE)
    if m:
        sha256_url = m.group(1).strip()
    reported_sha256 = None
    try:
        reported_sha256 = requests.get(sha256_url, timeout=10, allow_redirects=True, verify=True).text.strip()
        if re.match(r"^[A-Fa-f0-9]{64}$", reported_sha256):
            sha256sum = hashlib.sha256(script_content.encode('utf-8')).hexdigest()
            if sha256sum == reported_sha256:
                sha256sum_pass = True
            else:
                print(f"{colorama.Fore.RED}ERROR: SHA256 checksum mismatch! The script's SHA256 is {sha256sum} but the reported SHA256 is {reported_sha256}.{colorama.Style.RESET_ALL}")
        else:
            print(f"{colorama.Fore.YELLOW}WARN: The reported SHA256 from {sha256_url} is not a valid SHA256 hash.{colorama.Style.RESET_ALL}")
    except Exception as e:
        if sha256_url:
            print(f"{colorama.Fore.YELLOW}WARN: Failed to fetch the reported SHA256 from {sha256_url}.\n {e}{colorama.Style.RESET_ALL}")
        if isinstance(e, requests.exceptions.SSLError):
            print(f"""{colorama.Fore.RED}
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    @             WARNING: SSL CERTIFICATE ERROR!             @
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    IT'S POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
    There was an SSL certificate error while trying to fetch the SHA256sum.
    Someone could be intercepting your connection, or your source may not support HTTPS.
    For more information, visit: https://github.com/itzmetanjim/cursh/wiki
    {colorama.Style.RESET_ALL}""")
    # Check for PGP/GPG signature
    if os.WEXITSTATUS(os.system("gpg --version > /dev/null 2>&1")) == 0:
        pgp_url = None
        m = re.search(r"PGP\s?/\s?GPG\s?Signature\s?:\s?(.*)", script_content, re.IGNORECASE)
        if m:
            pgp_url = m.group(1).strip()
        try:
            if pgp_url:
                pgp_signature = requests.get(pgp_url, timeout=10, allow_redirects=True, verify=True).text
                with open(os.path.join(os.path.expanduser("~"), "cursh_last_script.sh.sig"), "w", encoding="utf-8") as f:
                    f.write(pgp_signature)
                ret = os.system(f"gpg --verify {os.path.join(os.path.expanduser('~'), 'cursh_last_script.sh.sig')} {os.path.join(os.path.expanduser('~'), 'cursh_last_script.sh')} > /dev/null 2>&1")
                if ret == 0:
                    pgp_pass = True
                else:
                    print(f"{colorama.Fore.RED}ERROR: PGP/GPG signature verification failed for the script.{colorama.Style.RESET_ALL}")
        except Exception as e:
            if pgp_url:
                print(f"{colorama.Fore.YELLOW}WARN: Failed to fetch the PGP/GPG signature from {pgp_url}.\n {e}{colorama.Style.RESET_ALL}")
            if isinstance(e, requests.exceptions.SSLError):
                print(f"""{colorama.Fore.RED}
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    @             WARNING: SSL CERTIFICATE ERROR!             @
    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    IT'S POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
    There was an SSL certificate error while trying to fetch the PGP/GPG signature.
    Someone could be intercepting your connection, or your source may not support HTTPS.
    For more information, visit: https://github.com/itzmetanjim/cursh/wiki
    {colorama.Style.RESET_ALL}""")
    else:
        print(f"{colorama.Fore.YELLOW}WARN: GPG is not installed or not found in PATH. Skipping PGP/GPG signature verification.{colorama.Style.RESET_ALL}")
    # Check if URL is in trusted list
    for app in trusted_data:
        url_pattern = app.get("url_pattern")
        match = re.fullmatch(url_pattern, url)
        if match is None:
            continue
        if url_pattern:
            trusted_list_match = True
        
        groups= list(match.groups())
        for i in app.get("valid_versions", [[]]):
            if groups == i:
                trusted_list_version_match = True
                break
        if trusted_list_match:
            break

    ############### DECISION MAKING ################
    # First, check if we are root or not
    is_root = (os.geteuid() == 0)
    if trusted_list_version_match and not is_root:
        os.execv("/bin/sh", ["/bin/sh", os.path.join(os.path.expanduser("~"), "cursh_last_script.sh")])
        # If execv fails
        print(f"{colorama.Fore.RED}ERROR: Failed to execute the script. It has been verified safe, you can run it yourself using sh ~/cursh_last_script.sh{colorama.Style.RESET_ALL}")
        sys.exit(1)
    if trusted_list_version_match:
        print(f"{colorama.Fore.GREEN}SAFE: The URL {url} is in the trusted list with a matching version..{colorama.Style.RESET_ALL}")
    elif trusted_list_match:
        print(f"{colorama.Fore.GREEN}PROBABLY SAFE: The URL {url} is in the trusted list, but this is an older/newer version than the one in the list.{colorama.Style.RESET_ALL}")
    if sha256sum_pass:
        print(f"{colorama.Fore.GREEN}SAFE: The script's SHA256 matches the reported SHA256.{colorama.Style.RESET_ALL}")
    else:
        print(f"{colorama.Fore.YELLOW}WARN: The script's SHA256 does not match the reported SHA256 or no SHA256 was reported.{colorama.Style.RESET_ALL}")
    if pgp_pass:
        print(f"{colorama.Fore.GREEN}SAFE: The script's PGP/GPG signature is valid.{colorama.Style.RESET_ALL}")
    else:
        print(f"{colorama.Fore.YELLOW}WARN: The script's PGP/GPG signature is invalid or no PGP/GPG signature was found.{colorama.Style.RESET_ALL}")
    if consistent_responses:
        print(f"{colorama.Fore.GREEN}SAFE: The server returned consistent responses for different user agents.{colorama.Style.RESET_ALL}")
    elif trusted_list_match:
        print(f"{colorama.Fore.YELLOW}WARN: The server returned inconsistent responses for different user agents.{colorama.Style.RESET_ALL}")
    else:
        print(f"{colorama.Fore.RED}ERROR: The server returned inconsistent responses for different user agents.{colorama.Style.RESET_ALL}")
        print(f"{colorama.Fore.RED}ABORTING: The URL {url} is NOT in the trusted list and the server returned inconsistent responses.{colorama.Style.RESET_ALL}")
        sys.exit(1)
    # Now, make a decision based on the checks
    print("-------------------------------------")
    if trusted_list_version_match:
        print(f"{colorama.Fore.GREEN}The script is from a trusted source and the version matches. You can run it safely.")
        print("However, since the command is being run as root, the command was not executed automatically.")
    elif trusted_list_match:
        print(f"{colorama.Fore.GREEN}The script is from a trusted source but the version is newer/older than expected")
        print("It's probably safe to run it, but you can verify the changes in the script before running it."+colorama.Style.RESET_ALL)
    elif sha256sum_pass:
        print(f"{colorama.Fore.GREEN}The script's SHA256 matches the reported SHA256.")
        print("If you are sure that the script source is trusted, you can run it as there were no transmission errors."+colorama.Style.RESET_ALL)
    elif pgp_pass:
        print(f"{colorama.Fore.GREEN}The script's PGP/GPG signature is valid."+colorama.Style.RESET_ALL)
    if trust_only and not trusted_list_match:
        print(f"{colorama.Fore.RED}ABORTING: The URL {url} is NOT in the trusted list and --trust_only was specified.{colorama.Style.RESET_ALL}")
        sys.exit(1)
    decline=False
    while not decline:
        print("Choose options:")
        print("1. Open the script in nano to view and/or edit it before running.")
        print("2. Don't run the script now, but save it to ~/cursh_last_script.sh for later inspection.")
        print("3. Run the script now.")
        choice = input("What now? (1/2/3): ").strip()
        if choice == '1':
            os.system(f"nano {os.path.join(os.path.expanduser('~'), 'cursh_last_script.sh')}")
            continue
        elif choice == '2':
            print(f"The script has been saved to {os.path.join(os.path.expanduser('~'), 'cursh_last_script.sh')}. You can inspect it and run it later if you deem it safe.")
            decline=True
        elif choice == '3':
            os.execv("/bin/sh", ["/bin/sh", os.path.join(os.path.expanduser("~"), "cursh_last_script.sh")])
            # If execv fails
            print(f"{colorama.Fore.RED}ERROR: Failed to execute the script. It has been saved to ~/cursh_last_script.sh, you can run it yourself using sh ~/cursh_last_script.sh{colorama.Style.RESET_ALL}")
            sys.exit(1)
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")
            continue
        
main()