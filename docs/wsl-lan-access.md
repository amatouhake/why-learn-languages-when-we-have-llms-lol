# WSL LAN アクセス設定

WSL上のサーバーに同一LAN内のスマホ等からアクセスするための設定。

## Enable

PowerShell（管理者として実行）:

```powershell
# WSLのIPを確認
wsl hostname -I

# ポートフォワード（<WSL_IP> を上で確認したIPに置き換える）
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress=<WSL_IP>

# ファイアウォール許可
netsh advfirewall firewall add rule name="HSK Trainer" dir=in action=allow protocol=TCP localport=8000
```

スマホから `http://<WindowsのIP>:8000` でアクセス。WindowsのIPは `ipconfig` の Wi-Fi IPv4 アドレス。

## Disable

```powershell
netsh interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0
netsh advfirewall firewall delete rule name="HSK Trainer"
```

## 確認

```powershell
# ポートフォワードの一覧
netsh interface portproxy show all

# ファイアウォールルールの確認
netsh advfirewall firewall show rule name="HSK Trainer"
```

## 注意

- WSL再起動でIPが変わることがある。その場合はポートフォワードを再設定する
- Pi にデプロイすれば不要になる設定（開発時のみ）
