import os
import time
import hashlib
from typing import Union, Optional

from flask import Flask, jsonify, request, session
from requests import HTTPError, TooManyRedirects, Timeout

import hdu_crawl
from dao import user_dao, admin_dao, server_info
from dao.admin_dao import Admin
from dao.user_config import UserConfig, save_user_config
from dao.user_dao import User, exist_account, login, exist_uid
import my_setting
import tempfile

my_setting.read_admin_password()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hui1abUIU,W<>Q{}@^T&^$T()(@$!!_H1FBV3VHG.xcdfghSX045D4FG5H51ug44848416'


@app.route('/api/get_rank')
def get_rank():
    """
    获取排行榜
    """
    return jsonify(status=True, users=user_dao.get_rank(), notice=server_info.get_notice())


@app.route('/api/login')
def login():
    """
    登录
    :return:
    """
    if 'uid' in request.args:
        uid = request.args.get('uid', type=str)
        pwd = request.args.get('pwd', type=str)
        if exist_uid(uid):
            user = login(uid, pwd)
            if user:
                session['user'] = user
                return jsonify(status=True, user=user)
            else:
                return jsonify(status=False, msg="账号与密码不匹配！")
        else:
            return jsonify(status=False, msg="账号不存在！")
    else:
        user = session.get('user', None)
        if user:
            return jsonify(status=True, user=user)
        else:
            return jsonify(status=False, mgs="请先登录！")


# def validate_account_without_get_request(account: str) -> Union[str, None]:
#     """
#     验证账号是否合法
#     :return: 合法返回None，否则返回原因。
#     """
#     try:
#         if hdu_crawl.exist_hdu_account(account):
#             if not User.exist_account(account):
#                 return None
#             else:
#                 return '账号已经存在！'
#         else:
#             return '输入的账号不正确！'
#     except (ConnectionError, HTTPError, Timeout, TooManyRedirects):
#         return '连接杭电OJ失败！'
#
def __validate_user(field: str, value):
    """
    验证字段
    :param field:
    :param value:
    :return:如果成功则返回None，否则返回json。
    """
    if field == 'uid':
        if value:
            current_user: Optional[User, None] = None
            if 'admin' not in session.keys():
                current_user = session.get('user', None)
                if not current_user:
                    return jsonify(status=False, mgs="请先登录！")
                else:
                    if current_user.id != value:
                        return jsonify(status=False, mgs="不允许修改别人账号！")

    if field == 'uid':
        if value is None or len(value) > 16:
            return jsonify(status=False, mgs="账号名长度不正确！")
        if user_dao.exist_uid(value):
            return jsonify(status=False, mgs="账号已被占用！")
    if field == 'pwd':
        if value is None or len(value) > 128:
            return jsonify(status=False, mgs="密码长度不正确！")
    if field == 'class_name':
        if len(value) > 24:
            return jsonify(status=False, mgs="班级名长度不正确！")
    if field == 'name':
        if value is None or len(value) > 16:
            return jsonify(status=False, mgs="姓名长度不正确！")
    if field == 'motto':
        if len(value) > 16:
            return jsonify(status=False, mgs="姓名长度不正确！")
    if field == 'account':
        if len(value) > 64:
            return jsonify(status=False, mgs="杭电账号名过长！")
        if exist_account(value):
            return jsonify(status=False, mgs="账号已经存在！")
        else:
            try:
                if not hdu_crawl.exist_hdu_account(value):
                    return jsonify(status=False, mgs="账号不存在，请确认输入是否正确！")
            except (ConnectionError, HTTPError, Timeout, TooManyRedirects):
                return jsonify(status=False, mgs="连接HDU失败！")

    return None


@app.route('/api/put_user')
def put_user():
    """
    添加或者修改用户
    :return:
    """
    user = User()
    for key in user.__dict__.keys():
        if key in request.args.keys():
            user.__dict__[key] = request.args.get(key)

    if user.id:
        for item in user.__dict__:
            if item[1]:
                res = __validate_user(item[0], item[1])
                if res:
                    return res
        user.update()
        current_user = session.get('user', None)
        if current_user and current_user.id == user.id:
            session['user'] = user
    else:
        for item in user.__dict__:
            res = __validate_user(item[0], item[1])
            if res:
                return res
        user.add()
    return jsonify(status=True)


@app.route('/api/validate_user')
def validate_user():
    """
    验证字段
    :return:
    """
    filed = request.args.get('field', type=str)
    value = request.args.get('value')
    val_res = __validate_user(filed, value)
    if val_res:
        return val_res
    else:
        return jsonify(status=True)


@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify(status=True)


@app.route('/api/remove')
def remove():
    """
    删除用户
    """
    id = request.args.get('id', type=int)
    user = User()
    user.id = id

    admin = session.get('admin', None)
    if not admin:
        current_user: Optional[User, None] = session.get('user', None)
        if not current_user:
            return jsonify(status=False, msg='请先登录！')
        else:
            if current_user.id != user.id:
                return jsonify(status=False, msg='不能删除别人账号！')
    user.remove()
    return jsonify(status=True)


@app.route('/api/login_admin')
def login_admin():
    """
    管理员登录
    :return:
    """

    if 'uid' in request.args.keys():
        uid = request.args.get('uid', type=str)
        pwd = request.args.get('pwd', type=str)

        if not admin_dao.exist_uid(uid):
            return jsonify(status=False, msg='账号不存在！')
        admin = admin_dao.login(uid, pwd)
        if not admin:
            return jsonify(status=False, msg='密码错误！')
    else:
        admin = session.get('admin', None)
        if not admin:
            return jsonify(status=False, msg='请先登录！')
    return jsonify(status=True, admin=admin)


@app.route('/api/list_admin')
def list_admin():
    """
    管理员列表
    :return:
    """
    admin: Optional[Admin, None]
    admin = session.get('admin', None)
    if admin and admin.is_super:
        return jsonify(status=True, admins=admin_dao.get_admin_list())
    else:
        return jsonify(status=False, msg='请先登录！')


def __validate_admin(field: str, value):
    if field == 'uid':
        if value is None or len(value) > 16:
            return jsonify(status=False, msg="字段不正确！")
        if admin_dao.exist_uid(value):
            return jsonify(status=False, msg="账号名已存在！")
    if field == 'pwd':
        if value is None or len(field) > 128:
            return jsonify(status=False, msg="字段长度不正确！")


@app.route('/api/validate_admin')
def validate_admin():
    admin: Admin = session.get('admin', None)
    if admin:
        filed = request.args.get('field', type=str)
        value = request.args.get('value')
        val_res = __validate_user(filed, value)
        if val_res:
            return val_res
        else:
            return jsonify(status=True)
    else:
        return jsonify(status=False, msg="请先登录！")


@app.route('/api/put_admin')
def put_admin():
    current_admin: Admin = session.get('admin', None)
    admin = Admin()
    for key in admin.__dict__.keys():
        if key in request.args.keys():
            admin.__dict__[key] = request.args.get(key)

    if current_admin:
        if admin.id:
            # 更新
            if admin.id == current_admin.id or current_admin.is_super:
                res = __validate_admin('uid', admin.uid) or __validate_admin('pwd', admin.pwd)
                if res:
                    return res
                admin.update()
            else:
                return jsonify(status=False, msg="没有权限！")
        else:
            # 创建
            if not admin.is_super:
                return jsonify(status=False, msg="没有权限！")
            for item in admin.__dict__:
                if item[1]:
                    res = __validate_admin(item[0], item[1])
                    if res:
                        return res
            admin.add()
    else:
        return jsonify(status=False, msg="请先登录！")
    return jsonify(status=True)


@app.route('/api/remove_admin')
def remove_admin():
    id = request.args.get('id', type=int)
    admin: Optional[Admin] = session.get('admin', None)
    if not admin:
        return jsonify(status=False, msg="请先登录！")
    if not admin.is_super:
        return jsonify(status=False, msg="没有权限！")
    admin_dao.remove_admin(id)
    return jsonify(status=True)


@app.route('/api/crawl_start')
def crawl_start():
    """
    开始滚版
    :return:
    """
    admin: Admin = session.get('admin', None)
    if admin:
        if hdu_crawl.crawl_status() == 'stopped':
            hdu_crawl.crawl_start()
            return jsonify(status=True)
        else:
            return jsonify(status=False, msg='已经在运行！')
    else:
        return jsonify(status=False, msg='请先登录！')


@app.route('/api/crawl_stop')
def crawl_stop():
    """
    停止滚榜
    :return:
    """
    admin: Admin = session.get('admin', None)
    if admin:
        if hdu_crawl.crawl_status() != 'stopped':
            hdu_crawl.crawl_stop()
            return jsonify(status=True)
        else:
            return jsonify(status=False, msg='已经停止！')
    else:
        return jsonify(status=False, msg='请先登录！')


@app.route('/api/crawl_status')
def crawl_status():
    """
    爬虫状态
    :return:
    """
    return jsonify(status=True, crawl_status=hdu_crawl.crawl_status())


@app.route('/api/add_notice')
def add_notice():
    """
    添加留言
    :return:
    """
    admin: Admin = session.get('admin', None)
    if admin:
        notice = request.args.get('notice', type=str)
        server_info.set_notice(notice)
        return jsonify(status=True)
    else:
        return jsonify(status=False, msg='请先登录！')


# hdu_crawl.crawl_start()
if __name__ == '__main__':
    app.run()
