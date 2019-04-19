# 该文件的名称必须要命名为tasks  不能随便取
# 编辑异步任务代码
from celery_tasks.sms.yuntongxun.sms import CCP
from celery_tasks.sms import constants
from celery_tasks.main import celery_app


@celery_app.task(name="send_sms_code")  # 使用装饰器注册任务  name是给任务起别名
def send_sms_code(mobile,sms_code):
    CCP().send_template_sms(mobile, [sms_code, constants.SMS_CODE_REDIS_EXPIRES / 60], 1)