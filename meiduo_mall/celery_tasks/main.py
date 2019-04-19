from celery import Celery
import os

# 告诉celery 如果需要使用django的配置文件  应该按照下面的内容去加载
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

# 创建celery实例对象
celery_app = Celery("meiduo")

# 加载配置文件
celery_app.config_from_object("celery_tasks.config")

# 自动注册异步任务
celery_app.autodiscover_tasks(["celery_tasks.sms","celery_tasks.email","celery_tasks.html"])

