from django.contrib import admin

from app.accounts import admin as accounts_admin
from app.classroom import admin as classroom_admin
from app.documents import admin as documents_admin
from app.editorial import admin as editorial_admin
from app.organizations import admin as organizations_admin
from app.quizzes import admin as quizzes_admin
from app.reporting import admin as reporting_admin
from app.routes import admin as routes_admin
from app.signs import admin as signs_admin


admin.site.site_header = 'Админ-панель «Знай ПДД»'
admin.site.site_title = 'Знай ПДД'
admin.site.index_title = 'Управление сайтом'
