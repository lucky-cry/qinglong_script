#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: kurobbs.py
Author: lucky-cry
Date: 2025/12/20 15:39
cron: 0 0 6 * * ?
库街区(Kurobbs)自动签到脚本 - 增强版
适配青龙面板环境变量
增加token自动刷新检测
"""

import os
import sys
import json
import time
import random
from datetime import datetime
from typing import List, Dict, Any

import requests

# 设置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class KurobbsClient:
    """库街区签到客户端"""
    
    def __init__(self, token: str, user_index: int = 1):
        self.token = token.strip()
        self.user_index = user_index
        self.session = requests.Session()
        
        if not self.token:
            raise ValueError("TOKEN不能为空")
            
        # 设备信息 - 随机化以防止检测
        devices = [
            {
                "model": "2211133C",
                "devcode": "2fba3859fe9bfe9099f2696b8648c2c6",
                "version": "1.0.9",
                "versioncode": "1090"
            },
            {
                "model": "23013RK75C",
                "devcode": "3a8b7c6d5e4f3a2b1c9d8e7f6a5b4c3d",
                "version": "1.1.0", 
                "versioncode": "1100"
            },
            {
                "model": "22081212C",
                "devcode": "4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
                "version": "1.0.8",
                "versioncode": "1080"
            }
        ]
        
        device = random.choice(devices)
        
        self.headers = {
            "osversion": "Android",
            "devcode": device["devcode"],
            "countrycode": "CN",
            "ip": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "model": device["model"],
            "source": "android",
            "lang": "zh-Hans",
            "version": device["version"],
            "versioncode": device["versioncode"],
            "token": self.token,
            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
            "accept-encoding": "gzip",
            "user-agent": f"okhttp/3.10.0 {device['model']}",
        }
        
        self.session.headers.update(self.headers)
        
    def _make_request(self, url: str, data: Dict[str, Any] = None, method: str = "POST") -> Dict[str, Any]:
        """发送请求"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method.upper() == "POST":
                    response = self.session.post(url, data=data, timeout=15)
                else:
                    response = self.session.get(url, params=data, timeout=15)
                
                response.raise_for_status()
                result = response.json()
                
                # 检查token是否过期
                if result.get("code") == 401 or "登录已过期" in str(result.get("msg", "")):
                    logger.error(f"账号{self.user_index}: Token已过期，请重新获取")
                    return {"code": 401, "msg": "登录已过期，请重新登录"}
                
                return result
                
            except requests.exceptions.Timeout:
                logger.warning(f"请求超时，第{attempt + 1}次重试...")
                time.sleep(2)
            except requests.exceptions.RequestException as e:
                logger.error(f"请求失败: {str(e)}")
                if attempt == max_retries - 1:
                    return {"code": 500, "msg": f"网络请求失败: {str(e)}"}
                time.sleep(1)
            except json.JSONDecodeError:
                logger.error("响应解析失败")
                return {"code": 500, "msg": "响应解析失败"}
        
        return {"code": 500, "msg": "请求失败"}
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        url = "https://api.kurobbs.com/user/mineV2"
        data = {"type": 1}
        return self._make_request(url, data)
    
    def get_game_roles(self, user_id: str) -> Dict[str, Any]:
        """获取游戏角色列表"""
        url = "https://api.kurobbs.com/gamer/role/default"
        data = {"queryUserId": user_id}
        return self._make_request(url, data)
    
    def game_sign(self) -> Dict[str, Any]:
        """执行游戏签到"""
        logger.info(f"账号{self.user_index}: 开始游戏签到...")
        
        # 获取用户信息
        user_result = self.get_user_info()
        if user_result.get("code") != 200:
            return user_result
        
        user_data = user_result.get("data", {})
        user_id = user_data.get("mine", {}).get("userId")
        
        if not user_id:
            return {"code": 400, "msg": "无法获取用户ID"}
        
        # 获取游戏角色
        roles_result = self.get_game_roles(str(user_id))
        if roles_result.get("code") != 200:
            return roles_result
        
        roles_data = roles_result.get("data", {})
        role_list = roles_data.get("defaultRoleList", [])
        
        if not role_list:
            return {"code": 400, "msg": "未找到游戏角色"}
        
        # 使用第一个角色
        role = role_list[0]
        current_month = datetime.now().strftime("%m")
        
        # 执行签到
        url = "https://api.kurobbs.com/encourage/signIn/v2"
        data = {
            "gameId": role.get("gameId", 2),
            "serverId": role.get("serverId"),
            "roleId": role.get("roleId"),
            "userId": role.get("userId"),
            "reqMonth": current_month,
        }
        
        return self._make_request(url, data)
    
    def forum_sign(self) -> Dict[str, Any]:
        """执行社区签到"""
        logger.info(f"账号{self.user_index}: 开始社区签到...")
        
        url = "https://api.kurobbs.com/user/signIn"
        data = {"gameId": 2}
        
        return self._make_request(url, data)
    
    def execute_all_sign(self) -> Dict[str, Any]:
        """执行所有签到"""
        results = {
            "user_index": self.user_index,
            "game_sign": None,
            "forum_sign": None,
            "success": False,
            "message": ""
        }
        
        # 游戏签到
        game_result = self.game_sign()
        results["game_sign"] = game_result
        
        if game_result.get("code") == 200 and game_result.get("success"):
            logger.info(f"账号{self.user_index}: 游戏签到成功")
        else:
            logger.warning(f"账号{self.user_index}: 游戏签到失败 - {game_result.get('msg')}")
        
        time.sleep(random.uniform(1, 3))  # 随机延迟
        
        # 社区签到
        forum_result = self.forum_sign()
        results["forum_sign"] = forum_result
        
        if forum_result.get("code") == 200 and forum_result.get("success"):
            logger.info(f"账号{self.user_index}: 社区签到成功")
        else:
            logger.warning(f"账号{self.user_index}: 社区签到失败 - {forum_result.get('msg')}")
        
        # 汇总结果
        game_success = game_result.get("success") or game_result.get("code") == 200
        forum_success = forum_result.get("success") or forum_result.get("code") == 200
        
        if game_success and forum_success:
            results["success"] = True
            results["message"] = "游戏和社区签到均成功"
        elif game_success:
            results["success"] = True
            results["message"] = "游戏签到成功，社区签到失败"
        elif forum_success:
            results["success"] = True
            results["message"] = "社区签到成功，游戏签到失败"
        else:
            results["message"] = "签到失败"
        
        return results


def format_results_for_notification(results_list: List[Dict[str, Any]]) -> str:
    """格式化通知消息"""
    success_count = sum(1 for r in results_list if r.get("success"))
    total_count = len(results_list)
    
    message = f"库街区签到完成 {success_count}/{total_count}\n"
    message += "=" * 30 + "\n"
    
    for result in results_list:
        idx = result.get("user_index", 0)
        status = "✅" if result.get("success") else "❌"
        msg = result.get("message", "")
        
        game_msg = ""
        if result.get("game_sign"):
            game_code = result["game_sign"].get("code")
            game_success = result["game_sign"].get("success", False)
            game_msg = "游戏:" + ("成功" if game_success or game_code == 200 else "失败")
        
        forum_msg = ""
        if result.get("forum_sign"):
            forum_code = result["forum_sign"].get("code")
            forum_success = result["forum_sign"].get("success", False)
            forum_msg = "社区:" + ("成功" if forum_success or forum_code == 200 else "失败")
        
        detail = f"{game_msg} {forum_msg}".strip()
        
        message += f"账号{idx}: {status} {msg}"
        if detail:
            message += f" ({detail})"
        message += "\n"
    
    return message


def send_notification(title: str, content: str):
    """发送通知"""
    # 青龙面板通知
    ql_notify = os.environ.get("QL_NOTIFY", "true").lower() == "true"
    
    if ql_notify:
        # 使用青龙内置的通知方式
        try:
            # 尝试导入青龙通知模块
            sys.path.append('/ql/scripts')
            try:
                from notify import send as ql_send
                ql_send(title, content)
                logger.info("已通过青龙通知发送")
                return
            except ImportError:
                pass
        except Exception as e:
            logger.warning(f"青龙通知发送失败: {e}")
    
    # 备用通知方式
    # 1. Bark
    bark_key = os.environ.get("BARK_KEY") or os.environ.get("BARK_PUSH")
    if bark_key:
        try:
            bark_url = f"https://api.day.app/{bark_key}/{title}/{content}"
            requests.get(bark_url, timeout=10)
            logger.info("已通过Bark发送通知")
        except Exception as e:
            logger.error(f"Bark通知发送失败: {e}")
    
    # 2. PushPlus
    pushplus_token = os.environ.get("PUSHPLUS_TOKEN")
    if pushplus_token:
        try:
            pushplus_url = "http://www.pushplus.plus/send"
            pushplus_data = {
                "token": pushplus_token,
                "title": title,
                "content": content,
                "template": "txt"
            }
            requests.post(pushplus_url, json=pushplus_data, timeout=10)
            logger.info("已通过PushPlus发送通知")
        except Exception as e:
            logger.error(f"PushPlus通知发送失败: {e}")
    
    # 3. Server酱
    serverchan_key = os.environ.get("SERVERCHAN_KEY") or os.environ.get("PUSH_KEY")
    if serverchan_key:
        try:
            serverchan_url = f"https://sctapi.ftqq.com/{serverchan_key}.send"
            serverchan_data = {
                "title": title,
                "desp": content
            }
            requests.post(serverchan_url, data=serverchan_data, timeout=10)
            logger.info("已通过Server酱发送通知")
        except Exception as e:
            logger.error(f"Server酱通知发送失败: {e}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("库街区自动签到脚本启动")
    logger.info("=" * 50)
    
    # 获取TOKEN
    token_env = os.environ.get("KUROBBS_TOKEN") or os.environ.get("TOKEN")
    
    if not token_env:
        logger.error("❌ 错误: 未设置TOKEN环境变量")
        logger.info("请在青龙面板环境变量中添加:")
        logger.info("名称: KUROBBS_TOKEN 或 TOKEN")
        logger.info("值: 你的库街区token（多账号用&分隔）")
        logger.info("")
        logger.info("如何获取TOKEN:")
        logger.info("1. 使用抓包工具（如HttpCanary）抓取库街区App请求")
        logger.info("2. 在请求头中找到token字段")
        logger.info("3. 注意：token有效期为7-30天，过期需要重新获取")
        return
    
    # 解析多个token
    tokens = []
    if "&" in token_env:
        tokens = [t.strip() for t in token_env.split("&") if t.strip()]
    elif "\n" in token_env:
        tokens = [t.strip() for t in token_env.split("\n") if t.strip()]
    else:
        tokens = [token_env.strip()]
    
    if not tokens:
        logger.error("❌ 错误: 未找到有效的TOKEN")
        return
    
    logger.info(f"📱 检测到 {len(tokens)} 个账号")
    
    # 执行签到
    all_results = []
    
    for idx, token in enumerate(tokens, 1):
        logger.info("-" * 40)
        logger.info(f"🔐 处理第 {idx} 个账号")
        
        try:
            client = KurobbsClient(token, user_index=idx)
            result = client.execute_all_sign()
            all_results.append(result)
            
            if result.get("success"):
                logger.info(f"✅ 账号{idx} 签到完成: {result.get('message')}")
            else:
                logger.warning(f"⚠️  账号{idx} 签到存在问题: {result.get('message')}")
                
        except Exception as e:
            logger.error(f"❌ 账号{idx} 执行出错: {str(e)}")
            all_results.append({
                "user_index": idx,
                "success": False,
                "message": f"执行出错: {str(e)}"
            })
        
        # 账号间延迟
        if idx < len(tokens):
            delay = random.uniform(3, 8)
            logger.info(f"等待 {delay:.1f} 秒后处理下一个账号...")
            time.sleep(delay)
    
    logger.info("=" * 50)
    
    # 统计结果
    success_count = sum(1 for r in all_results if r.get("success"))
    total_count = len(all_results)
    
    logger.info(f"📊 签到统计: 成功 {success_count}/{total_count}")
    
    # 生成通知消息
    notification_message = format_results_for_notification(all_results)
    
    # 发送通知
    if all_results:
        notification_title = f"库街区签到({success_count}/{total_count})"
        
        # 如果全部失败，标题改为失败
        if success_count == 0:
            notification_title = f"库街区签到失败({total_count}个账号)"
        
        send_notification(notification_title, notification_message)
    
    # 打印结果
    print("\n" + "=" * 50)
    print(notification_message)
    print("=" * 50)
    
    # 如果有token过期的账号，给出提示
    token_expired = any(
        "过期" in str(r.get("message", "")) or 
        (r.get("game_sign") and r["game_sign"].get("code") == 401) or
        (r.get("forum_sign") and r["forum_sign"].get("code") == 401)
        for r in all_results
    )
    
    if token_expired:
        print("\n⚠️  检测到有TOKEN过期，请按以下步骤重新获取：")
        print("1. 使用抓包工具（如HttpCanary）抓取库街区App")
        print("2. 找到任意api.kurobbs.com的请求")
        print("3. 复制请求头中的token字段")
        print("4. 在青龙面板中更新对应的TOKEN")
        print("\n📱 推荐抓包工具：")
        print("  - Android: HttpCanary、抓包精灵")
        print("  - iOS: Stream、Thor")
        print("=" * 50)
    
    # 设置退出码
    if success_count == 0:
        sys.exit(1)
    elif success_count < total_count:
        sys.exit(2)  # 部分成功


if __name__ == "__main__":
    # 检查依赖
    try:
        import requests
    except ImportError:
        print("❌ 缺少requests库，请执行: pip3 install requests")
        sys.exit(1)
    
    main()
