# grok

*a silly tool to query Github repository metadata*

## Getting started

### Create a personal access token

Generate a public read-only [personal access token](https://github.com/settings/personal-access-tokens/new). Back up the token somewhere safe, then use it in our configuration in the next step

### Create a configuration `~/.config/grok.tolm`

```bash
cat << EOF > ~/.config/grok.toml
[system]
auth_key = "your key goes here"
default_org = "holmanb"
default_repo = "grok"
default_mode = "all"
EOF
```

Be sure to set your key, default organization, and default repo in the configuration.

### Install grok

```bash
pip install --user grk
```

4. Run grok

```bash
grok
```
