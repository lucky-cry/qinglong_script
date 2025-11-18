# -*- coding: utf-8 -*-
"""
cron: 1 0 0 * * *
new Env('SteamTools');
"""

from sendNotify import send
from curl_cffi import requests
import re
import os

class SteamTools:
    def __init__(self, cookie, username):
        self.cookie = cookie
        self.username = username
        self.formhash = ''

    def check_cookie(self):
        """检查cookie有效性并获取formhash"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Cookie': self.cookie,
            'Referer': 'https://bbs.steamtools.net/'
        }
        
        try:
            response = requests.get(
                'https://bbs.steamtools.net/forum.php?mod=viewthread&tid=8741',
                headers=headers,
                timeout=15,
                verify=False,
                impersonate="chrome120"
            )
            
            if response.status_code != 200:
                return False, f"页面访问失败，状态码: {response.status_code}"
                
            # 提取formhash
            searchObj = re.search(r'name="formhash" value="(.+?)"', response.text)
            if not searchObj:
                return False, "无法获取formhash，Cookie可能已失效"
                
            self.formhash = searchObj.group(1)
            
            # 验证用户名
            if self.username not in response.text:
                return False, "Cookie验证失败，用户名不匹配"
                
            return True, "Cookie验证成功"
            
        except Exception as e:
            return False, f"检查Cookie时出错: {str(e)}"

    def do_signin(self):
        """执行签到"""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': self.cookie,
            'Referer': 'https://bbs.steamtools.net/forum.php?mod=viewthread&tid=8741',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Origin': 'https://bbs.steamtools.net'
        }
        
        data = f'formhash={self.formhash}&signsubmit=yes&handlekey=signin&emotid=3&referer=https%3A%2F%2Fbbs.steamtools.net%2Fforum.php%3Fmod%3Dviewthread%26tid%3D8741&content=%E4%B8%BA%E4%BA%86%E7%BB%B4%E6%8A%A4%E5%AE%87%E5%AE%99%E5%92%8C%E5%B9%B3%EF%BC%8C%E6%89%93%E8%B5%B7%E7%B2%BE%E7%A5%9E%E6%9D%A5%EF%BC%81%7E%7E'
        
        try:
            response = requests.post(
                'https://bbs.steamtools.net/plugin.php?id=dc_signin:sign&inajax=1',
                headers=headers,
                data=data,
                timeout=30,
                verify=False,
                impersonate="chrome120"
            )
            
            if "您今日已经签过到" in response.text:
                return True, "已经签到过了，不再重复签到!"
            elif "签到成功" in response.text or "succeedhandle_signin" in response.text:
                return True, "签到成功!"
            else:
                return False, f"签到失败: {response.text}"
                
        except Exception as e:
            return False, f"签到请求失败: {str(e)}"

    def start(self):
        """主流程"""
        print("[*] 开始steamtools签到任务")
        
        # 检查Cookie
        success, message = self.check_cookie()
        if not success:
            print(f"[-] {message}")
            send("steamtools 签到结果", f"❌ 失败: {message}")
            return
        
        print(f"[+] {message}")
        
        # 执行签到
        success, result = self.do_signin()
        
        # 发送通知
        if success:
            print(f"[+] {result}")
            send("steamtools 签到结果", f"✅ SteamTools签到成功!\n{result}")
        else:
            print(f"[-] {result}")
            send("steamtools 签到结果", f"❌ SteamTools签到失败!\n{result}")

if __name__ == "__main__":
    cookie = os.getenv("STEAMTOOLS_COOKIE")
    username = os.getenv("STEAMTOOLS_USER")
    
    if not cookie or not username:
        print("[-] 请设置 STEAMTOOLS_COOKIE 和 STEAMTOOLS_USER 环境变量")
        send("steamtools 签到结果", "❌ 环境变量未设置完整")
    else:
        SteamTools(cookie, username).start()
