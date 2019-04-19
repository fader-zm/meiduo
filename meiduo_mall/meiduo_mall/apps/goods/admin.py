from django.contrib import admin
from . import models
from celery_tasks.html.tasks import generate_static_list_search_html, generate_static_sku_detail_html


class GoodsCategoryAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """当点击admin站点的保存按钮时 回来调用此方法
        request 保存时本次请求对象
        obj 本次要保存的模型对象
        form admin中的表单"""
        obj.save()
        # 保存之后 重新生成静态页面
        generate_static_list_search_html.delay()

    def delete_model(self, request, obj):
        """当点击admin中的删除按钮时 会调用此方法"""
        obj.delete()
        # 保存之后 重新生成静态页面(耗时操作)
        generate_static_list_search_html.delay()


# @admin.register(models.SKU)
class SKUAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        generate_static_sku_detail_html.delay(obj.id)


class SKUImageAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        # obj是图片模型对象
        # sku_id = obj.sku_id
        sku = obj.sku  # 通过外键获取图片模型对象所关联的sku模型id
        if not sku.default_image_url:
            sku.default_image_url = obj.image.url
        generate_static_sku_detail_html.delay(sku.id)

    def delete_model(self, request, obj):
        obj.delete()
        sku = obj.sku
        generate_static_sku_detail_html.delay(sku.id)


admin.site.register(models.GoodsCategory, GoodsCategoryAdmin)
admin.site.register(models.GoodsChannel)
admin.site.register(models.Goods)
admin.site.register(models.Brand)
admin.site.register(models.GoodsSpecification)
admin.site.register(models.SpecificationOption)
admin.site.register(models.SKU, SKUAdmin)
admin.site.register(models.SKUSpecification)
admin.site.register(models.SKUImage, SKUImageAdmin)
