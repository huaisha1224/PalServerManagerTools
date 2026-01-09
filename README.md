<h1 align='center'>幻兽帕鲁服务器管理工具</h1>
<p align='center'>
基于REST API可视化界面管理幻兽帕鲁专用服务器，服务器MOD安装等功能
</p>

基于官方提供的 REST API 实现功能：
- [x] 获取服务器信息
- [x] 获取服务器指标数据
- [x] 在线玩家列表
- [x] 踢出/封禁玩家
- [x] 游戏内广播
- [x] 平滑关闭服务器并广播消息

工具额外提供的功能：

- [x] 可视化地图管理
- [x] 存档自动备份与管理
- [x] 服务器MOD安装和卸载

- [ ] 

帕鲁服务器管理工具交流：<a target="_blank" href="https://qm.qq.com/q/Czyyy07ojY"><img border="0" src="https://pub.idqqimg.com/wpa/images/group.png" alt="帕鲁服务器管理工具" title="帕鲁服务器管理工具"></a>
![加QQ群](./docs/img/add_group.jpg)


## 开启 REST API和配置管理员密码

本项目必需开启服务器的 REST API 功能才能正常使用

如果你的服务器还没有配置好，请先关闭服务端，然后在 [Pal-Conf](https://pal-conf.bluefissure.com/) 修改 `PalWorldSettings.ini` 启用服务端。
先设置 **管理员密码**
再设置 **REST API**
