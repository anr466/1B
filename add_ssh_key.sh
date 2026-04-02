#!/bin/bash
# Script to add SSH public key to authorized_keys
# Run this on the remote server

mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add the public key
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC0eGWwB6knWNnGCON1b5wcHKg9OhfqgXaT7vF1K3VA3QsGbAi13FlLzyHcKxc06NfFskL2h/zIlY9nzTm1L+BQHNEF1V4Xn2JkF6uEVi2WxUQNLgUI0XqVFsx8yso8CEnUjqjR9hLVusiLmbPBZsvHF1j8pPaq2e7lp/sd8DzobDgaFdRAVzvGK67COHvFdWFK7gR6nkfLnx+SQzjBDdquMNcZ0HeapvetvFN0P5ockIL3WJrMWoZIbk6v3VGmwZBy7DXjTZo3tkkbJG8k86uva3StgjhcKMsVTCubzkVNNQnpbNbCPOr5yxXbCb0IArTkuSWt5hN6xbJxs5WERJ60ljhf6l1QEsNyBbj/YQ0zD07uHgrkqnxh0fBXujYDFZ5Fo5fHOZ/h+IzzJqsXV/6m7LptG2CJQJZRpflkVGumdYeXb6Uk2/CKbHd0hAVTF7va3oq2hkUOczB1ym4YE6XrNRGX/scMIDBX76gICkbt3SkW7kkTkoyuZJNQ2ICWuOE= anranr466@gmail.com" >> ~/.ssh/authorized_keys

chmod 600 ~/.ssh/authorized_keys
echo "✅ SSH key added successfully!"
