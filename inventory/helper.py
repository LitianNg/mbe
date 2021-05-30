from django.core.paginator import Paginator

def paginate(object, page =1, limit = 10):
    paginator = Paginator(object, limit) # Show 25 contacts per page.

    page_obj = paginator.get_page(page)
    return page_obj