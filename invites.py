#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: invites.py
Author: lucky-cry
Date: 2025/10/21 15:39
cron: 0 0 6 * * ?
new Env('邀玩（药丸）自动签到');
Description: 邀玩（药丸）自动签到
Update: 2025/10/21 修复Cookie刷新机制
"""
import os
import sys
from bs4 import BeautifulSoup
import json
import requests
import logging
import re
import initialize


def get_refreshed_session(user_cookie):
    """
    获取刷新后的session
    返回: (session_data, refreshed_cookie)
    """
    url = 'https://invites.fun/'
    
    # 从原始cookie中提取flarum_remember
    remember_match = re.search(r'flarum_remember=([^;]+)', user_cookie)
    if not remember_match:
        initialize.error_message("Cookie中未找到flarum_remember")
        return None, None
    
    flarum_remember = remember_match.group(1)
    
    headers = {
        'Host': 'invites.fun',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Microsoft Edge";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-ch-ua-mobile': '?0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.43',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Dest': 'document',
        'Referer': 'https://invites.fun/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cookie': f'flarum_remember={flarum_remember}'  # 只使用remember来获取新session
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 从响应头中获取刷新的flarum_session
        set_cookie = response.headers.get('Set-Cookie', '')
        session_match = re.search(r'flarum_session=([^;]+)', set_cookie)
        
        refreshed_session = None
        if session_match:
            refreshed_session = session_match.group(1)
            initialize.info_message("成功获取刷新后的session")
        else:
            # 如果没有新的session，尝试从原有cookie中提取
            old_session_match = re.search(r'flarum_session=([^;]+)', user_cookie)
            if old_session_match:
                refreshed_session = old_session_match.group(1)
                initialize.info_message("使用原有session")
        
        # 解析页面数据获取用户信息
        soup = BeautifulSoup(response.content.decode('utf-8'), "html.parser")
        script_tag = soup.find('script', attrs={'id': 'flarum-json-payload'})
        if not script_tag:
            initialize.error_message("未找到用户数据")
            return None, None
            
        soup_data = script_tag.text
        parsed_data = json.loads(soup_data)
        session_data = parsed_data.get("session", {})
        
        if not session_data:
            initialize.error_message("解析用户数据失败")
            return None, None
            
        # 构建刷新后的完整cookie
        refreshed_cookie = f"flarum_remember={flarum_remember}; flarum_session={refreshed_session}"
        
        return session_data, refreshed_cookie
        
    except Exception as e:
        initialize.error_message(f"获取刷新session失败: {str(e)}")
        return None, None


def sign_in(user_session, refreshed_cookie):
    """执行签到"""
    user_id = user_session.get('userId')
    csrf_token = user_session.get('csrfToken')
    
    if not user_id:
        initialize.error_message("获取不到用户id")
        return False
        
    if not csrf_token:
        initialize.error_message("获取不到CSRF Token")
        return False

    initialize.info_message(f"用户id：{user_id} 开始签到")

    url = f"https://invites.fun/api/users/{user_id}"

    headers = {
        "Host": "invites.fun",
        "Connection": "keep-alive",
        "sec-ch-ua": '"Chromium";v="116", "Not)A;Brand";v="24", "Microsoft Edge";v="116"',
        "X-CSRF-Token": csrf_token,
        "sec-ch-ua-mobile": "?0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62",
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/vnd.api+json, application/json, text/plain, */*",
        "X-HTTP-Method-Override": "PATCH",
        "sec-ch-ua-platform": '"Windows"',
        "Origin": "https://invites.fun",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://invites.fun/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cookie": refreshed_cookie  # 使用刷新后的cookie
    }

    data = {
        "data": {
            "type": "users",
            "attributes": {
                "canCheckin": False,
                "totalContinuousCheckIn": 1
            },
            "id": user_id
        }
    }

    try:
        response = requests.patch(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            res_parsed_data = json.loads(response.text)
            attributes = res_parsed_data["data"]["attributes"]
            username = attributes["username"]
            total_continuous_check_in = attributes["totalContinuousCheckIn"]
            initialize.info_message(f"用户 {username} 签到成功，已连续签到 {total_continuous_check_in} 天")
            return True
        else:
            initialize.error_message(f"签到失败，状态码: {response.status_code}")
            initialize.info_message(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        initialize.error_message(f"签到请求异常: {str(e)}")
        return False


def check_cookie_validity(user_session):
    """检查cookie是否有效"""
    if not user_session:
        return False
        
    user_id = user_session.get('userId')
    csrf_token = user_session.get('csrfToken')
    
    if not user_id or not csrf_token:
        return False
        
    return True


if __name__ == "__main__":
    initialize.init()
    initialize.info_message("开始邀玩（药丸）自动签到\n")
    
    if os.environ.get("INVITES_COOKIE"):
        cookies = os.environ.get("INVITES_COOKIE")
    else:
        initialize.error_message("请在环境变量中填写INVITES_COOKIE的值")
        sys.exit()

    success_count = 0
    total_count = len(cookies.split("&"))
    
    for i, cookie in enumerate(cookies.split("&"), 1):
        initialize.info_message(f"处理第 {i}/{total_count} 个账号")
        
        # 获取刷新后的session和cookie
        session, refreshed_cookie = get_refreshed_session(cookie.strip())
        
        if not check_cookie_validity(session):
            initialize.error_message("Cookie无效或已过期，请更新Cookie")
            continue
            
        if sign_in(session, refreshed_cookie):
            success_count += 1
            
        logging.info('\n')
        initialize.message('\n')

    # 发送通知
    initialize.send_notify(f"邀玩（药丸）签到完成 - 成功: {success_count}/{total_count}")
