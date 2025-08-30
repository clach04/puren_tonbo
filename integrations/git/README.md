# git integration with Puren Tonbo for encrypted and compressed files

## Setup

Need to edit two files in a checkout:

  1. `.git/config` (or `.git\config`)
  2. `.gitattributes`

### Setup .git/config

Edit `.git/config` (or `.git\config`) and
add a section, for example at the end:

```
# https://git-scm.com/docs/gitattributes#_generating_diff_text
# encrypted diff
[diff "ptdiff"]
	textconv = ptcipher --decrypt
	cachetextconv = false
	# don't cache secrets on disk!
```

Alternatively:

Unix/Linux/BSD:

    cat config >> YOUR_GIT_CHECKOUT_DIR/.git/config

Windows:

    type config >> YOUR_GIT_CHECKOUT_DIR\.git\config

### Setup .gitattributes

Edit `.gitattributes` and
add a section, for example at the end:

```
# compressed - treat as encrypted diff for consistent diff tool - with https://github.com/clach04/puren_tonbo/issues/210
*.gz diff=ptdiff
*.Z diff=ptdiff

# encrypted diff - with https://github.com/clach04/puren_tonbo/issues/210
*.age diff=ptdiff
*.gpg diff=ptdiff
*.asc diff=ptdiff
*.openssl_aes256cbc_pbkdf2_10k diff=ptdiff
*.chi diff=ptdiff
*.chs diff=ptdiff
*.cpt diff=ptdiff
*.jenc diff=ptdiff
*.u001.jenc diff=ptdiff
*.u001_jenc diff=ptdiff
*.v001.jenc diff=ptdiff
*.v001_jenc diff=ptdiff
*.v002.jenc diff=ptdiff
*.v002_jenc diff=ptdiff
*.rot13 diff=ptdiff
*.rot47 diff=ptdiff
*.vimcrypt diff=ptdiff
*.vimcrypt1 diff=ptdiff
*.vimcrypt2 diff=ptdiff
*.vimcrypt3 diff=ptdiff
*.old.zip diff=ptdiff
*.oldstored.zip diff=ptdiff
*.zip diff=ptdiff
*.aes.zip diff=ptdiff
*.aes256.zip diff=ptdiff
*.aeszip diff=ptdiff
*.aes256bzip2.zip diff=ptdiff
*.aes256lzma.zip diff=ptdiff
*.aes256stored.zip diff=ptdiff
```
Alternatively:

Unix/Linux/BSD:

    cat gitattributes >> YOUR_GIT_CHECKOUT_DIR/.gitattributes

Windows:

    type gitattributes >> YOUR_GIT_CHECKOUT_DIR\.gitattributes

