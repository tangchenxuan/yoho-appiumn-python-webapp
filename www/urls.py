#!/usr/bin/env python
# -*- coding: utf-8 -*-



import os, re, time, base64, hashlib, logging

import markdown2

from transwarp.web import get, post, ctx, view, interceptor, seeother, notfound

from apis import api, Page, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError
from models import User, Pageviews
from config import configs

_COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

def _get_page_index():
    page_index = 1
    try:
        page_index = int(ctx.request.get('page', '1'))
    except ValueError:
        pass
    return page_index

def make_signed_cookie(id, password, max_age):
    # build cookie string by: id-expires-md5
    expires = str(int(time.time() + (max_age or 86400)))
    L = [id, expires, hashlib.md5('%s-%s-%s-%s' % (id, password, expires, _COOKIE_KEY)).hexdigest()]
    return '-'.join(L)

def parse_signed_cookie(cookie_str):
    try:
        L = cookie_str.split('-')
        if len(L) != 3:
            return None
        id, expires, md5 = L
        if int(expires) < time.time():
            return None
        user = User.get(id)
        if user is None:
            return None
        if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, _COOKIE_KEY)).hexdigest():
            return None
        return user
    except:
        return None

def check_admin():
    user = ctx.request.user
    if user and user.admin:
        return
    raise APIPermissionError('No permission.')

@interceptor('/')
def user_interceptor(next):
    logging.info('try to bind user from session cookie...')
    user = None
    cookie = ctx.request.cookies.get(_COOKIE_NAME)
    if cookie:
        logging.info('parse session cookie...')
        user = parse_signed_cookie(cookie)
        if user:
            logging.info('bind user <%s> to session...' % user.email)
    ctx.request.user = user
    return next()

@interceptor('/manage/')
def manage_interceptor(next):
    user = ctx.request.user
    if user and user.admin:
        return next()
    raise seeother('/signin')

@view('signin.html')
@get('/')
def index():
    pageviews, page = _get_pageviews_by_page()
    return dict(page=page, pageviews=pageviews, user=ctx.request.user)



@view('pageviews.html')
@get('/pageviews/:page_id')
def pageviews(page_id):
    pageview = Pageviews.get(page_id)
    if pageview is None:
        raise notfound()
    pageview.html_content = markdown2.markdown(pageview.page_value)
    #comments = Comment.find_by('where blog_id=? order by created_at desc limit 1000', blog_id)
    return dict(pageview=pageview, user=ctx.request.user)



@view('signin.html')
@get('/signin')
def signin():
    return dict()

@get('/signout')
def signout():
    ctx.response.delete_cookie(_COOKIE_NAME)
    raise seeother('/')

@api
@post('/api/authenticate')
def authenticate():
    i = ctx.request.input(remember='')
    email = i.email.strip().lower()
    password = i.password
    remember = i.remember
    user = User.find_first('where email=?', email)
    if user is None:
        raise APIError('auth:failed', 'email', 'Invalid email.')
    elif user.password != password:
        raise APIError('auth:failed', 'password', 'Invalid password.')
    # make session cookie:
    max_age = 604800 if remember=='true' else None
    cookie = make_signed_cookie(user.id, user.password, max_age)
    ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
    user.password = '******'
    return user

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_MD5 = re.compile(r'^[0-9a-f]{32}$')

@api
@post('/api/users')
def register_user():
    i = ctx.request.input(name='', email='', password='')
    name = i.name.strip()
    email = i.email.strip().lower()
    password = i.password
    if not name:
        raise APIValueError('name')
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    if not password or not _RE_MD5.match(password):
        raise APIValueError('password')
    user = User.find_first('where email=?', email)
    if user:
        raise APIError('register:failed', 'email', 'Email is already in use.')
    user = User(name=name, email=email, password=password, image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email).hexdigest())
    user.insert()
    # make session cookie:
    cookie = make_signed_cookie(user.id, user.password, None)
    ctx.response.set_cookie(_COOKIE_NAME, cookie)
    return user

@view('register.html')
@get('/register')
def register():
    return dict()

def _get_pageviews_by_page():
    total = Pageviews.count_all()
    page = Page(total, _get_page_index())
    pageviews = Pageviews.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    return pageviews, page

@get('/manage/')
def manage_index():
    raise seeother('/manage/pageviews')

#@view('manage_comment_list.html')
#@get('/manage/comments')
#def manage_comments():
#    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_pageview_list.html')
@get('/manage/pageviews')
def manage_pageviews():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@view('manage_pageview_edit.html')
@get('/manage/pageviews/create')
def manage_pageviews_create():
    return dict(id=None, action='/api/pageviews', redirect='/manage/pageviews', user=ctx.request.user)

@view('manage_pageview_edit.html')
@get('/manage/pageviews/edit/:page_id')
def manage_pagevies_edit(page_id):
    pageview = Pageviews.get(page_id)
    if pageview is None:
        raise notfound()
    return dict(id=pageview.id, page_name=pageview.page_name, element=pageview.element, byway=pageview.byway, page_value=pageview.page_value, action='/api/pageviews/%s' % page_id, redirect='/manage/pageviews', user=ctx.request.user)

@view('manage_user_list.html')
@get('/manage/users')
def manage_users():
    return dict(page_index=_get_page_index(), user=ctx.request.user)

@api
@get('/api/pageviews')
def api_get_pageviews():
    format = ctx.request.get('format', '')
    pageview, page = _get_pageviews_by_page()
    if format=='html':
        for pageview in pageview:
            pageview.page_value = markdown2.markdown(pageview.page_value)
    return dict(pageviews=pageview, page=page)

@api
@get('/api/pageviews/:page_id')
def api_get_pageview(page_id):
    pageview = Pageviews.get(page_id)
    if pageview:
        return pageview
    raise APIResourceNotFoundError('Pageview')

@api
@post('/api/pageviews')
def api_create_pageview():
    check_admin()
    i = ctx.request.input(page_name='', element='', byway='', page_value='')
    page_name = i.page_name.strip()
    element = i.element.strip()
    byway = i.byway.strip()
    page_value = i.page_value.strip()
    if not page_name:
        raise APIValueError('page_name', 'name cannot be empty.')
    if not element:
        raise APIValueError('element', 'summary cannot be empty.')
    if not byway:
        raise APIValueError('byway', 'content cannot be empty.')
    if not page_value:
        raise APIValueError('page_value', 'content cannot be empty.')
    user = ctx.request.user
    pageview = Pageviews(user_id=user.id, user_name=user.name, page_name=page_name, element=element, byway=byway, page_value=page_value)
    pageview.insert()
    return pageview

@api
@post('/api/pageviews/:page_id')
def api_update_pageview(page_id):
    check_admin()
    i = ctx.request.input(page_name='', element='', byway='', page_value='')
    page_name = i.page_name.strip()
    element = i.element.strip()
    byway = i.byway.strip()
    page_value = i.page_value.strip()
    if not page_name:
        raise APIValueError('page_name', 'name cannot be empty.')
    if not element:
        raise APIValueError('element', 'summary cannot be empty.')
    if not byway:
        raise APIValueError('byway', 'content cannot be empty.')
    if not page_value:
        raise APIValueError('page_value', 'content cannot be empty.')
    pageview = Pageviews.get(page_id)
    if pageview is None:
        raise APIResourceNotFoundError('Page')
    pageview.page_name = page_name
    pageview.element = element
    pageview.byway = byway
    pageview.page_value = page_value
    pageview.update()
    return pageview

@api
@post('/api/pageviews/:page_id/delete')
def api_delete_pageview(page_id):
    check_admin()
    pageview = Pageviews.get(page_id)
    if pageview is None:
        raise APIResourceNotFoundError('Pageview')
    pageview.delete()
    return dict(id=page_id)

#@api
#@post('/api/0/:blog_id/comments')
#def api_create_blog_comment(blog_id):
#    user = ctx.request.user
#    if user is None:
#        raise APIPermissionError('Need signin.')
#    blog = Blog.get(blog_id)
#    if blog is None:
#        raise APIResourceNotFoundError('Blog')
#    content = ctx.request.input(content='').content.strip()
#    if not content:
#        raise APIValueError('content')
#    c = Comment(blog_id=blog_id, user_id=user.id, user_name=user.name, user_image=user.image, content=content)
#    c.insert()
#    return dict(comment=c)

#@api
#@post('/api/comments/:comment_id/delete')
#def api_delete_comment(comment_id):
#    check_admin()
#    comment = Comment.get(comment_id)
#    if comment is None:
#        raise APIResourceNotFoundError('Comment')
#    comment.delete()
#    return dict(id=comment_id)

#@api
#@get('/api/comments')
#def api_get_comments():
#    total = Comment.count_all()
#    page = Page(total, _get_page_index())
#    comments = Comment.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
#    return dict(comments=comments, page=page)

@api
@get('/api/users')
def api_get_users():
    total = User.count_all()
    page = Page(total, _get_page_index())
    users = User.find_by('order by created_at desc limit ?,?', page.offset, page.limit)
    for u in users:
        u.password = '******'
    return dict(users=users, page=page)
