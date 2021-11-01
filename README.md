# SonnyBot-ng

## Replit Deployment Instructions

Firstly, clone this repo into `~/SonnyBot`

Then, create a ssh key.  Prefer `ed25519` crypto as it gives smaller
public key, is much faster and more secure compared to `rsa`.  Save the
generated public/private key pair *inside* `~/SonnyBot/`!! **Not
`~/.ssh/`!!**  Replit will destroy any file not in `~/SonnyBot/`.

Now edit the private key.  Originally the file should look like this:
```
-----BEGIN OPENSSH PRIVATE KEY-----
blah blah blah
-----END OPENSSH PRIVATE KEY-----
```
Add a newline, and then add some junk.  For example:
```
-----BEGIN OPENSSH PRIVATE KEY-----
blah blah blah
-----END OPENSSH PRIVATE KEY-----

replit sucks <-- junk added
```
Otherwise replit will "helpfully" strip off the final newline and
corrupt the private key.

Now go to @OTHScodingbot and configure the above generated public key as
a deploy key at appropriate data repository (probably `data-production`
if it is the production instance).  **Enable write access!!**

Now run
```sh
GIT_SSH_COMMAND="ssh -i $PRIVATE_KEY_HERE" git clone $REPO_HERE data
cd data

# Tell git to use our private key to push/pull
# DO NOT use ~/.ssh/config, replit will destroy anything not in ~/SonnyBot/
# Also inhibit prompt for host key confirmation, since there is no one there to answer yes
git config core.sshCommand "ssh -o 'StrictHostKeyChecking no' -i $PRIVATE_KEY_HERE"

# Configure username and email
git config user.name $BOT_USER_NAME_HERE
git config user.email $BOT_EMAIL_HERE
```

Set a replit secret named `BOT_TOKEN` containing the discord token.
Click run.
