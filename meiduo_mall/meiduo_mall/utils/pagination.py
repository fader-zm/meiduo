from rest_framework.pagination import PageNumberPagination


class StandardResultSetPagination(PageNumberPagination):
    """自定义分页类"""
    page_size = 2
    max_page_param = 5
    page_query_param = "page"   # 默认就是page  前端用来指定显示第几页的查询关键字
    page_size_query_param = "page_size"   # 前端用来指定每页显示多少条数据的 关键字
