#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
库街区(Kurobbs)自动签到脚本
适配青龙面板环境变量
"""

import os
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests

# 设置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Response(BaseModel):
    """响应模型"""
    code: int = Field(..., alias="code", description="返回值")
    msg: str = Field(..., alias="msg", description="提示信息")
    success: Optional[bool] = Field(None, alias="success", description="token有时才有")
    data: Optional[Any] = Field(None, alias="data", description="请求成功才有")


class KurobbsClientException(Exception):
    """自定义异常"""


class KurobbsClient:
    """库街区客户端"""
    
    # API地址
    FIND_ROLE_LIST_API_URL = "https://api.kurobbs.com/gamer/role/default"
    SIGN_URL = "https://api.kurobbs.com/encourage/signIn/v2"
    USER_SIGN_URL = "https://api.kurobbs.com/user/signIn"
    USER_MINE_URL = "https://api.kurobbs.com/user/mineV2"

    def __init__(self, token: str):
        if not token:
            raise KurobbsClientException("TOKEN is required to call Kurobbs APIs.")

        self.token = token
        self.session = requests.Session()
        self.session.headers.update(
            {
                "osversion": "Android",
                "devcode": "2fba3859fe9bfe9099f2696b8648c2c6",
                "countrycode": "CN",
                "ip": "10.0.2.233",
                "model": "2211133C",
                "source": "android",
                "lang": "zh-Hans",
                "version": "1.0.9",
                "versioncode": "1090",
                "token": self.token,
                "content-type": "application/x-www-form-urlencoded; charset=utf-8",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/3.10.0",
            }
        )
        self.result: Dict[str, str] = {}
        self.exceptions: List[Exception] = []

    def _post(self, url: str, data: Dict[str, Any]) -> Response:
        """发送POST请求"""
        try:
            response = self.session.post(url, data=data, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise KurobbsClientException(f"Request to {url} failed: {exc}") from exc

        try:
            res = Response.model_validate_json(response.content)
        except Exception as exc:
            raise KurobbsClientException(f"Failed to parse response from {url}") from exc

        logger.debug(
            "POST %s -> code=%s, success=%s, msg=%s",
            url, res.code, res.success, res.msg
        )
        return res

    def get_mine_info(self, type: int = 1) -> Dict[str, Any]:
        """获取用户信息"""
        res = self._post(self.USER_MINE_URL, {"type": type})
        if not res.data:
            raise KurobbsClientException("User info is missing in response.")
        return res.data

    def get_user_game_list(self, user_id: int) -> Dict[str, Any]:
        """获取用户游戏列表"""
        res = self._post(self.FIND_ROLE_LIST_API_URL, {"queryUserId": user_id})
        if not res.data:
            raise KurobbsClientException("User game list is missing in response.")
        return res.data

    def checkin(self) -> Response:
        """执行游戏签到"""
        mine_info = self.get_mine_info()
        user_game_list = self.get_user_game_list(user_id=mine_info.get("mine", {}).get("userId", 0))

        beijing_tz = ZoneInfo("Asia/Shanghai")
        beijing_time = datetime.now(beijing_tz)

        role_list = user_game_list.get("defaultRoleList") or []
        if not role_list:
            raise KurobbsClientException("No default role found for the user.")
        role_info = role_list[0]

        data = {
            "gameId": role_info.get("gameId", 2),
            "serverId": role_info.get("serverId"),
            "roleId": role_info.get("roleId", 0),
            "userId": role_info.get("userId", 0),
            "reqMonth": f"{beijing_time.month:02d}",
        }
        return self._post(self.SIGN_URL, data)

    def sign_in(self) -> Response:
        """执行社区签到"""
        return self._post(self.USER_SIGN_URL, {"gameId": 2})

    def _process_sign_action(
        self,
        action_name: str,
        action_method: Callable[[], Response],
        success_message: str,
        failure_message: str,
    ):
        """处理签到动作"""
        try:
            resp = action_method()
            if resp.success:
                self.result[action_name] = success_message
                logger.info("%s -> %s", action_name, success_message)
            else:
                self.exceptions.append(KurobbsClientException(f"{failure_message}, {resp.msg}"))
        except Exception as e:
            self.exceptions.append(KurobbsClientException(f"{failure_message}: {str(e)}"))

    def start(self):
        """开始签到流程"""
        # 游戏签到
        self._process_sign_action(
            action_name="checkin",
            action_method=self.checkin,
            success_message="游戏签到成功",
            failure_message="游戏签到失败",
        )

        # 社区签到
        self._process_sign_action(
            action_name="sign_in",
            action_method=self.sign_in,
            success_message="社区签到成功",
            failure_message="社区签到失败",
        )

        self._log()

    @property
    def msg(self) -> str:
        """获取结果消息"""
        if self.result:
            return "🎉 " + ", ".join(self.result.values())
        return ""

    def _log(self):
        """记录日志"""
        if msg := self.msg:
            logger.info(msg)
        if self.exceptions:
            error_msg = "; ".join(map(str, self.exceptions))
            logger.error(error_msg)
            raise KurobbsClientException(error_msg)


def send_notification(title: str, content: str):
    """发送通知（适配青龙面板的通知方式）"""
    # 青龙面板环境变量
    push_config = {
        # Bark通知
        "BARK_PUSH": os.environ.get("BARK_PUSH", ""),
        "BARK_SOUND": os.environ.get("BARK_SOUND", ""),
        
        # Server酱
        "PUSH_KEY": os.environ.get("PUSH_KEY", ""),
        
        # 企业微信
        "QYWX_AM": os.environ.get("QYWX_AM", ""),
        
        # Telegram
        "TG_BOT_TOKEN": os.environ.get("TG_BOT_TOKEN", ""),
        "TG_USER_ID": os.environ.get("TG_USER_ID", ""),
        
        # PushPlus
        "PUSH_PLUS_TOKEN": os.environ.get("PUSH_PLUS_TOKEN", ""),
        "PUSH_PLUS_USER": os.environ.get("PUSH_PLUS_USER", ""),
    }
    
    # 这里可以根据实际需要添加通知逻辑
    # 青龙面板会自动处理通知，所以我们只需要打印消息
    logger.info("通知标题: %s", title)
    logger.info("通知内容: %s", content)
    
    # 如果有自定义通知需求，可以在这里添加


def main():
    """主函数"""
    # 从青龙环境变量获取TOKEN
    token = os.environ.get("KUROBBS_TOKEN") or os.environ.get("TOKEN")
    
    if not token:
        logger.error("未找到TOKEN，请检查环境变量")
        sys.exit(1)
    
    # 支持多个账号（青龙格式：用&或换行分隔）
    tokens = []
    if "&" in token:
        tokens = token.split("&")
    elif "\n" in token:
        tokens = token.split("\n")
    else:
        tokens = [token]
    
    all_results = []
    all_errors = []
    
    for i, token in enumerate(tokens, 1):
        token = token.strip()
        if not token:
            continue
            
        logger.info("=" * 40)
        logger.info("开始执行第 %d 个账号", i)
        
        try:
            client = KurobbsClient(token)
            client.start()
            
            if client.msg:
                all_results.append(f"账号{i}: {client.msg}")
                
        except KurobbsClientException as e:
            error_msg = f"账号{i}: {str(e)}"
            all_errors.append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"账号{i}: 未知错误 - {str(e)}"
            all_errors.append(error_msg)
            logger.error(error_msg)
    
    logger.info("=" * 40)
    
    # 汇总结果
    if all_results:
        final_msg = "\n".join(all_results)
        logger.info("执行成功:\n%s", final_msg)
        
        # 发送成功通知
        if all_errors:
            final_msg += f"\n\n❌ 失败账号:\n" + "\n".join(all_errors)
        
        # 发送通知
        send_notification("库街区签到成功", final_msg)
        
    elif all_errors:
        final_msg = "\n".join(all_errors)
        logger.error("所有账号都失败了:\n%s", final_msg)
        
        # 发送失败通知
        send_notification("库街区签到失败", final_msg)
        sys.exit(1)
    else:
        logger.info("没有账号需要执行")


if __name__ == "__main__":
    # 检查是否是青龙面板环境
    is_qinglong = os.environ.get("QL_DIR") or os.environ.get("QL_BRANCH")
    if is_qinglong:
        logger.info("检测到青龙面板环境")
    
    main()
