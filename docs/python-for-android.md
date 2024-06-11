1. Use WSL! It does not work directly on windows, so wsl makes the process as painless as possible
2. Follow the setup steps closely in https://python-for-android.readthedocs.io/en/latest/quickstart/
3. Until the step "Android SKD" use apt-get
4. The sdk itself can be installed rather easily through apt-get itself
5. Registry editing starts here
    1. Install the vscode wsl extension
    2. Use `code ~/.bashrc` to edit the bashrc
    3. Restart the wsl after you edit this with `wsl --shutdown` (execute from the windows terminal)
6. Put the following in there
```bash
# Android SDK stuff
export ANDROID_HOME=/usr/lib/android-sdk
export PATH=$ANDROID_HOME/cmdline-tools/tools/bin:$PATH

export ANDROIDSDK="$ANDROID_HOME/cmdline-tools"
export ANDROIDNDK="$ANDROID_HOME/android-ndk-r25b"
export ANDROIDAPI="31"  # Target API version of your application
export NDKAPI="21"  # Minimum supported API version of your application
export ANDROIDNDKVER="r25b"  # Version of the NDK you installed
```
7. The sdkmanager is usally not just installed by itself. Use this stackoverflow article: https://stackoverflow.com/questions/53994924/sdkmanager-command-not-found-after-installing-android-sdk
    - Important follow the advice "export PATH=$ANDROID_HOME/cmdline-tools/latest/tools/bin:$PATH seems to be correct, the /tools/ segment was missing in your command"
5. Use wget to get the ndk. You can then move it to the "$ANDROID_HOME" path
9. You can now use the sdkmanager from there
10. Make sure the android sdk versions you install (next steps in the installation guide) are reflected in the `./bashrc` (edit the 
bashrc, if you need to)
11. You can finally execute the commands