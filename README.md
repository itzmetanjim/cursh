# cursh
[Download/View Video](https://hc-cdn.hel1.your-objectstorage.com/s/v3/02f8a8b7bebee93e3a847d4e6e9fe97569bb1a20_2025-10-02_12-42-47.mp4)
Protect your Linux PC from viruses using a safer alternative to `curl ... | sh` or `wget ... | sh`
## Installation
`cursh` is only available on linux. The same instructions apply when updating.
1) Download the binary:
```bash
wget -O cursh https://github.com/itzmetanjim/cursh/raw/refs/heads/main/exec/cursh
```
2) Make it executable
```bash
sudo chmod +x cursh
```
3) Copy it to `/usr/bin/local/`:
```bash
sudo cp ./cursh /usr/local/bin/
sudo chmod +x /usr/local/bin/cursh
```

> If you are installing a second time or updating, simply overwrite the previous cursh file.

## Uninstall
Simply delete the executable.
```bash
sudo rm -f /usr/local/bin/cursh
```
Optionally, delete the config file:
```bash
rm ~/cursh.json
```
## How it works
It will use multiple verification steps. At any of these steps, if HTTPS/TLS auth fails, it will immediately abort. Also, if it has root priveleges, it will ALWAYS ask the user before executing, even if it determined it as safe.
When asking the user, these are the options the user has:
- Check the script, maybe edit it, then run it.
- Save the script.
- Do nothing (dont run)
- Run anyway (not recommended)

1) Check if the patterm matches `trusted.json` (hosted here and updated). If so,
    - Check the version list. If the version also matches, then its trusted.
    - If version does not match, ask the user first.
2) If its not in `trusted.json`,
    1) Check for the first line containing `SHA256:`. If found, check the URL for an SHA256 sum. If it matches, save the result to a variable.
    2) Check for the first line containing `PGP/GPG signature:`. If found, check the URL and see if the PGP is valid and matches the file. If so, save that to another variable.
    3) Check what the domain is and look it up in some trusted domains API (unless its something like Github)
    4) Request the URL with different user agents. Check if they are the same as the result with the `curl` user agent.
    5) Display all these results to the user and let the user decide one of four options.

## Files
- `trusted.json`: database of trusted scripts
- `check.py`: check if all the URLs are valid.
       
