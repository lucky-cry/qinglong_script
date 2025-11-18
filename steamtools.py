# -*- coding: utf-8 -*-
"""
cron: 1 0 0 * * *
new Env('SteamTools');
"""

from sendNotify import send
from curl_cffi import requests
import re
import os
import time
import json

class SteamTools(object):
    def __init__(self, cookie, username):
        self.cookie = cookie
        self.username = username
        self.formhash = ''

    def check_cookie(self):
        """检查cookie有效性并获取formhash"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Cookie': self.cookie,
        }
        
        try:
            response = requests.get(
                'https://bbs.steamtools.net/forum.php?mod=viewthread&tid=8741',
                headers=headers,
                timeout=15,
                verify=False
            )
            
            if response.status_code != 200:
                return False, f"页面访问失败，状态码: {response.status_code}"
                
            # 提取formhash
            searchObj = re.search(r'<input type="hidden" name="formhash" value="(.+?)" />', response.text)
            if not searchObj:
                return False, "无法获取formhash，Cookie可能已失效"
                
            self.formhash = searchObj.group(1)
            
            # 验证用户名
            if self.username not in response.text:
                return False, "Cookie验证失败，用户名不匹配"
                
            return True, f"Cookie验证成功，formhash: {self.formhash}"
            
        except Exception as e:
            return False, f"检查Cookie时出错: {str(e)}"

    def do_signin(self):
        """执行签到"""
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': self.cookie,
            'Referer': 'https://bbs.steamtools.net/forum.php?mod=viewthread&tid=8741',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }
        
        data = {
            'formhash': self.formhash,
            'signsubmit': 'yes',
            'handlekey': 'signin',
            'emotid': '3',
            'referer': 'https://bbs.steamtools.net/forum.php?mod=viewthread&tid=8741',
            'content': '为了维护宇宙和平，打起精神来！~~'
        }
        
        try:
            response = requests.post(
                'https://bbs.steamtools.net/plugin.php?id=dc_signin:sign&inajax=1',
                headers=headers,
                data=data,
                timeout=30,
                verify=False,
                impersonate="chrome110"
            )
            
            if "您今日已经签过到" in response.text:
                return True, "已经签到过了，不再重复签到!"
            elif "签到成功" in response.text:
                return True, "签到成功!"
            else:
                return False, f"签到失败，响应: {response.text}"
                
        except Exception as e:
            return False, f"签到请求失败: {str(e)}"

    def start(self):
        """主流程"""
        print("[*] 开始steamtools签到任务")
        
        # 1. 检查Cookie
        success, message = self.check_cookie()
        if not success:
            print(f"[-] {message}")
            send("steamtools 签到结果", f"失败: {message}")
            return
        
        print(f"[+] {message}")
        
        # 2. 执行签到
        success, result = self.do_signin()
        
        # 3. 发送通知
        if success:
            print(f"[+] {result}")
            send("steamtools 签到结果", f"✅ 签到成功!\n{result}")
        else:
            print(f"[-] {result}")
            send("steamtools 签到结果", f"❌ 签到失败!\n{result}")

if __name__ == "__main__":
    cookie = os.getenv("STEAMTOOLS_COOKIE")
    username = os.getenv("STEAMTOOLS_USER")
    
    if not cookie or not username:
        print("[-] 请设置 STEAMTOOLS_COOKIE 和 STEAMTOOLS_USER 环境变量")
        send("steamtools 签到结果", "❌ 环境变量未设置完整")
    else:
        SteamTools(cookie, username).start()
