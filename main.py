from aiocqhttp import MessageSegment
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.message.components import ComponentType, Reply
from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)


@register("astrbot_plugin_qgm", "moemoli", "一款智能管理群聊的插件", "0.0.2")
class GMPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    async def can_approve(
        self, event: AiocqhttpMessageEvent, uid: int, comment: str | None
    ):
        """根据条件判断是否可以通过审核"""
        reason = "等级不足"
        info = await event.bot.get_stranger_info(user_id=uid)
        i_level = info.get("qqLevel", 0)  # qq等级
        i_level_head = info.get("isHideQQLevel", 0)  # 是否隐藏QQ等级
        g_level = await self.get_kv_data(f"{event.get_group_id()}_level", "1")
        if g_level is None:
            g_level = "1"
        if i_level_head == 1:
            reason = "隐藏QQ等级"
        return (i_level_head != 1 and i_level >= int(g_level)), reason

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("进群审核")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def gm_cmd_request(self, event: AiocqhttpMessageEvent, enable: str):
        """这是一个开启群聊审核开关的指令"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        if enable not in ["开", "关"]:
            yield event.plain_result(
                "参数错误，请使用 进群审核 开 或 进群审核 关"
            )  # 发送一条纯文本消息
            return
        elif enable == "开":
            await self.put_kv_data(f"{event.get_group_id()}", "1")
            yield event.plain_result("已经开启本群的进群审核功能")  # 发送一条纯文本消息
        else:
            await self.delete_kv_data(event.get_group_id())
            yield event.plain_result("已经关闭本群的进群审核功能")  # 发送一条纯文本消息

    @filter.command("自动拒绝")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def gm_cmd_reject(self, event: AiocqhttpMessageEvent, enable: str):
        """这是一个开启群聊审核开关的指令"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        if enable not in ["开", "关"]:
            yield event.plain_result(
                "参数错误，请使用 自动拒绝 开 或 自动拒绝 关"
            )  # 发送一条纯文本消息
            return
        elif enable == "开":
            await self.put_kv_data(f"{event.get_group_id()}_reject", "1")
            yield event.plain_result("已经开启本群的自动拒绝功能")  # 发送一条纯文本消息
        else:
            await self.delete_kv_data(f"{event.get_group_id()}_reject")
            yield event.plain_result("已经关闭本群的自动拒绝功能")  # 发送一条纯文本消息

    @filter.command("进群等级")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def gm_cmd_join(self, event: AiocqhttpMessageEvent, level: int):
        """这是一个设置群聊审核等级的指令"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        if level < 1:
            yield event.plain_result(
                "参数错误，等级必须大于等于1"
            )  # 发送一条纯文本消息
            return
        await self.put_kv_data(f"{event.get_group_id()}_level", str(level))
        yield event.plain_result(
            f"已经设置本群的进群审核等级为: {level}"
        )  # 发送一条纯文本消息

    @filter.command("撤回")
    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def gm_cmd_revoke(self, event: AiocqhttpMessageEvent):
        """这是一个撤回指定消息的指令"""  # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        for msg in event.message_obj.message:
            if msg.type == ComponentType.Reply and isinstance(msg, Reply):
                await event.bot.delete_msg(message_id=int(msg.id))

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    @filter.platform_adapter_type(filter.PlatformAdapterType.AIOCQHTTP)
    async def gm_event_request(self, event: AiocqhttpMessageEvent):
        """监听进群/退群事件"""
        raw = event.message_obj.raw_message
        if isinstance(raw, dict):
            post_type = raw.get("post_type", "")
            if post_type == "request":
                logger.info(f"收到加群请求事件，内容为: {raw}")
                gid = raw.get("group_id", 0)
                enable = await self.get_kv_data(gid, None)
                if enable != None:
                    uid = raw.get("user_id", 0)
                    flag = raw.get("flag", "")
                    sub_type = raw.get("sub_type", "")
                    comment = raw.get("comment", None)
                    if isinstance(comment, str):
                        start = "答案："
                        comment = comment[comment.find(start) + len(start) :].strip()
                    approved, reason = await self.can_approve(event, uid, comment)
                    if comment is None:
                        comment = "(无)"
                    if approved:
                        logger.info(f"用户 {uid} 通过审核，自动同意加群")
                        await event.bot.set_group_add_request(
                            flag=flag,
                            sub_type=sub_type,
                            approve=True,
                        )
                        await event.bot.send_group_msg(
                            message=MessageSegment.text(
                                f"用户 {uid}  通过审核，已自动同意加群。\n申请内容: {comment}"
                            ),
                            group_id=gid,
                        )
                    else:
                        if await self.get_kv_data(f"{gid}_reject", None) is None:
                            logger.info(f"用户 {uid} 未能通过审核，忽略: {comment}")
                            await event.bot.send_group_msg(
                                message=MessageSegment.text(
                                    f"用户 {uid}  未能通过审核，请手动处理。\n申请内容: {comment}\n原因: {reason}"
                                ),
                                group_id=gid,
                            )
                        else:
                            await event.bot.set_group_add_request(
                                flag=flag,
                                sub_type=sub_type,
                                approve=False,
                                reason=reason,
                            )
                            await event.bot.send_group_msg(
                                message=MessageSegment.text(
                                    f"用户 {uid}  未能通过审核，已自动拒绝。\n申请内容: {comment}\n原因: {reason}"
                                ),
                                group_id=gid,
                            )

                else:
                    logger.info(f"群 {gid} 未配置，忽略")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
