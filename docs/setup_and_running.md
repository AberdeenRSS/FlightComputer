Install and use python3.11

```
sudo apt install python3.11-dev
pip install -r requirements.txt
git submodule update --init --recursive
cd submodules/tinyproto
git checkout stable_v1
pip install ./
```

Vscode press F5 or 
```
python3.11 -m kivy_wrapper

OR 

python3.11 -m standalone
```