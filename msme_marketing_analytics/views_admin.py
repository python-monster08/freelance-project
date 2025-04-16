from api.v1.accounts.serializers import ForgetPasswordSerializer
from cambridge.logs import logException
from api.v1.user_management.utils import SearchUserRecord
from api.v1.user_management.views_admin_serializers import *
from cambridge.message import *
from cambridge.pagination import CambridgeDefaultPaginationClass, TTCambridgeDefaultPaginationClass
from cambridge.permissions import *
from cambridge.response import *
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
import pandas as pd
import json
from django.template.loader import render_to_string
import re
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import AccessToken
from django.http import HttpResponse
from django.contrib import messages
from django.template.loader import render_to_string
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from itertools import chain
from django.db.models import Q
from rest_framework import filters
from collections import defaultdict
from rest_framework.exceptions import AuthenticationFailed
from django.db.models import Count
### web login
class TeacherLogInViewset(ModelViewSet):
    serializer_class = TeacherLoginSerializer

    http_method_names = ["post"]
    def get_queryset(self):
        return UserMaster.objects.all()
    
    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        

        serializer = TeacherLoginSerializer(data=request.data)
        if serializer.is_valid():       
            user=UserMaster.objects.filter(Q(email=email)|Q(username=email)).last()
            remember_me = request.data.get('remember_me',None)
            # user.is_access_updated=False
            user.save()
            serializer_data = TeacherDetailsSerializer(user,context={'remember_me':remember_me,'request':request,'user':user}).data
            return http_200_response(message=USER_LOGIN,data=serializer_data)
        else:
            if list(serializer.errors.keys())[0] != "error":
                return http_400_response(message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}")
            else:
                return http_400_response(message=serializer.errors[list(serializer.errors.keys())[0]][0])

class AppChangePasswordView(ModelViewSet):
    permission_classes = (AllowAny, )
    http_method_names = ['post']
    throttle_scope = 'app_change_password'  
    # throttle_classes = [VerifyOtpThrottle] 


    def get_serializer_class(self):
            if self.action == 'create':
                self.serializer_class = AppChangePasswordSerializer
                return AppChangePasswordSerializer

    def create(self,request):
            serializer = AppChangePasswordSerializer(data=request.data,context={"request":request})
            if serializer.is_valid():
                return http_200_response(message="Password changed successfully")
            else:
                if list(serializer.errors.keys())[0] != "error":
                    return http_200_response_false_response(message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}",)
                else:
                    return http_200_response_false_response(message= serializer.errors[list(serializer.errors.keys())[0]][0])

class AppForgetPasswordViewset(ModelViewSet):
    serializer_class = ForgetPasswordSerializer
    http_method_names = ["post"]
    def create(self, request):
        # try:
            email = request.data.get('email')
            user_role = UserMaster.objects.filter(email=email,user_role_id__in=[6,]).last()
            if user_role:
                user = UserMaster.objects.filter(email=email).last()
                if user:
                    expt = datetime.datetime.now()
                    uid = user.email
                    subject= "Forgot Password"
                    link = "api/v1/reset_password.html"
                    recipient_list = [email,MY_EMAIL]
                    cc_email= recipient_list
                    token = reset_password_access_token(user)
                    # link_change_password = f"{request.scheme}://" +request.get_host()+ "/account/v1/web_change_password/"+str(token)
                    link_change_password = f"{request.scheme}://" +request.get_host()+ "/accounts/v1/change_password_confirmation/"+str(token)
                    html_message = render_to_string(link, {'some_params': link_change_password})
                    # forget_password_mail(subject,recipient_list,cc_email,html_message)
                    # try:
                    email_message = EmailMessage(
                        subject=subject,
                        body=html_message,
                        from_email="triazinedev@gmail.com",
                        to=recipient_list,
                        cc=recipient_list,
                    )
                    email_message.content_subtype = "html"  # Ensure HTML email is sent
                    email_message.send()         
                    return http_200_response(message=FORGOT_PASSWORD_MESSAGE,data=link_change_password) 
                    # except Exception as e:
                    #     logException(e)
                    #     return http_500_response(error=str(e))   
                else:
                    return http_400_response(message="User not exists")
                
            else:
                return http_400_response(message="You are not allowed to reset your password.")


# active and inactive
class ActiveInactiveUserViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    serializer_class = ActiveInactiveUserStatusSerializer
    http_method_names = ['post']
    def create(self,request):
        user_id = request.data.get('user_id')
        if user_id:
            user_check = UserMaster.objects.filter(id = user_id).last()
            if user_check:
                # if request.data['is_active']:
                #     mapped_users = set(AssignWarehouseUserMapping.objects.filter(user_id = int(user_id),is_active=True).values_list("user__is_active",flat=True))
                #     if False in mapped_users:
                #         return http_400_response(message="Unable to activate this product because its User is inactive.") 
                serializer = ActiveInactiveUserStatusSerializer(data=request.data)
                if serializer.is_valid():
                    data =serializer.data
                    if data['is_active']==True:
                        return http_200_response(message=ACTIVE,data=data)
                    else:
                        return http_200_response(message=INACTIVE,data=data)
                else:
                    if list(serializer.errors.keys())[0] != "error":
                        return http_400_response(message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}")
                    else:
                        return http_400_response(message=serializer.errors[list(serializer.errors.keys())[0]][0])        
            else:
                return http_400_response(message=USER_ID)
        else:
            return http_400_response(message=NO_USER)


### Sub admin all api
class SubAdminRegisterView(ModelViewSet):
    permission_classes = (IsAuthenticated,AccessToSubAdmin) 
    http_method_names = ['get', 'post', 'put', 'delete']
    serializer_class = SubAdminRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    # parser_classes = (FormParser, MultiPartParser)
 
    def get_serializer_class(self):
        if self.action == "create":
            return SubAdminRegisterSerializer
        elif self.action == "retrieve":
            return GetSubAdminSerializer
        elif self.action == "update":
            return UpdateSubAdminSerializer
        else:
            return self.serializer_class



    def create(self, request, *args, **kwargs):
        try:
            if not request.auth:
                raise AuthenticationFailed("Invalid or missing access token.")

            if request.user.user_role_id in [1,2,]:
                serializer = self.get_serializer(data=request.data,context={"request":request,})
                serializer.context['request'] = request  
                if serializer.is_valid():
                    serializer.save()  
                    return http_201_response(message="User created successfully")
                else:
                    if list(serializer.errors.keys())[0] != "error":
                        return http_400_response(message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}")
                    else:
                        return http_400_response(message=serializer.errors[list(serializer.errors.keys())[0]][0])
            else:
                return http_400_response(message=UNAUTHORIZED)
        except Exception as e:
            return http_500_response(error=str(e))
        

    # type_search = openapi.Parameter('search',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    # # type_role = openapi.Parameter('role_id',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    # type_status = openapi.Parameter('status',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    # @swagger_auto_schema(manual_parameters=[type_search,type_status])
    # def list(self,request):
    #     try:

    #         search = self.request.query_params.get('search')
    #         role_id = self.request.query_params.get('role_id')
    #         status = self.request.query_params.get('status')

    #         if role_id:
    #             queryset = UserMaster.objects.filter(user_role_id=role_id,is_deleted=False,is_active=True)
    #         else:
    #             queryset = UserMaster.objects.filter(user_role_id__in=[2,],is_deleted=False,is_active=True,created_by_id=request.user.id).order_by('-created_on')

            
    #         queryset = queryset.values('id','employee_id','full_name','email','profile_picture','phone_number','user_role_id','user_role__role','address','description','is_active','created_on','assigned_by','assigned_by__full_name','created_by','created_by__full_name').order_by('-created_on')
            
    #         if status=="active":
    #             queryset=queryset.filter(is_active=True).all().order_by('-created_on')
    #         elif status=="inactive":
    #             queryset=queryset.filter(is_active=False).all().order_by('-created_on')
    #         else:
    #             queryset=queryset

    #         dataframe_df = pd.DataFrame((queryset))

    #         if not dataframe_df.empty:
            
    #             for index,row in dataframe_df.iterrows():
    #                 if dataframe_df.at[index,"profile_picture"]:
    #                     dataframe_df.at[index,"image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/"+str(dataframe_df.at[index,"profile_picture"])
    #                     # dataframe_df.at[index,"image"] = S3_BUCKET_BASE_URL+str(dataframe_df.at[index,"profile_picture"])

    #                 else:
    #                     dataframe_df.at[index,"image"] = ""

    #             dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

    #             # Check if 'id' column exists in dataframe_df
    #             if 'id' not in dataframe_df.columns:
    #                 return http_200_response(message=NOT_FOUND,data=[])

              
    #             if dataframe_df.empty:
    #                 return http_200_response(message=NOT_FOUND,data=[])

    #             ## rename
    #             dataframe_df.rename(columns={'role__role': 'role_name', 'bio': 'description', 'full_name': 'name',
    #                                         'state__name': 'state_name', 'city__name': 'city_name', 'phone_number': 'phone_number','assigned_by__full_name':'assigned_by_name','created_by__full_name':'created_by_name'}, inplace=True)
    #             if search:
    #                 search = search.strip()
    #                 search = re.escape(search)
    #                 dataframe_df = SearchUserRecord(dataframe_df, search)
                
    #             if 'created_on' in dataframe_df.columns:
    #                 dataframe_df['created_on'] = dataframe_df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p')if pd.notna(x) else 'Invalid Date')
    #             else:
    #                 dataframe_df['created_on'] = ""

    #             ## drop
    #             dataframe_df.drop(columns=['profile_picture'],inplace=True)

    #             dataframe_df = dataframe_df.fillna("")
    #             json_list = dataframe_df.to_json(orient='records')
    #             json_list = json.loads(json_list)
    #             paginator = CambridgeDefaultPaginationClass()
    #             paginator.message = DATA_FOUND_SUCCESS
    #             result_page = paginator.paginate_queryset(json_list, request)
    #             return paginator.get_paginated_response(result_page)
    #         else:
    #             return http_200_response_pagination(message=NOT_FOUND)

    #     except Exception as e:
    #         logException(e)
    #         return http_500_response(error=str(e))

    type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_order_by = openapi.Parameter('order_by', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Sort by 'name' or 'email'")

    @swagger_auto_schema(manual_parameters=[type_search, type_status, type_order_by])
    def list(self, request):
        try:
            search = self.request.query_params.get('search')
            role_id = self.request.query_params.get('role_id')
            status = self.request.query_params.get('status')
            order_by = self.request.query_params.get('order_by')

            if role_id:
                queryset = UserMaster.objects.filter(user_role_id=role_id, is_deleted=False, is_active=True)
            else:
                queryset = UserMaster.objects.filter(user_role_id__in=[2,], is_deleted=False, is_active=True, created_by_id=request.user.id).order_by('-created_on')

            queryset = queryset.values(
                'id', 'employee_id', 'full_name', 'email', 'profile_picture', 'phone_number',
                'user_role_id', 'user_role__role', 'address', 'description', 'is_active',
                'created_on', 'assigned_by', 'assigned_by__full_name', 'created_by', 'created_by__full_name'
            ).order_by('-created_on')

            dataframe_df = pd.DataFrame((queryset))

            if not dataframe_df.empty:
                for index, row in dataframe_df.iterrows():
                    if dataframe_df.at[index, "profile_picture"]:
                        dataframe_df.at[index, "image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/" + str(dataframe_df.at[index, "profile_picture"])
                    else:
                        dataframe_df.at[index, "image"] = ""

                dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

                if 'id' not in dataframe_df.columns:
                    return http_200_response(message=NOT_FOUND, data=[])

                if dataframe_df.empty:
                    return http_200_response(message=NOT_FOUND, data=[])

                dataframe_df.rename(columns={
                    'role__role': 'role_name',
                    'bio': 'description',
                    'full_name': 'name',
                    'state__name': 'state_name',
                    'city__name': 'city_name',
                    'phone_number': 'phone_number',
                    'assigned_by__full_name': 'assigned_by_name',
                    'created_by__full_name': 'created_by_name'
                }, inplace=True)

                if search:
                    search = search.strip()
                    search = re.escape(search)
                    dataframe_df = SearchUserRecord(dataframe_df, search)

                # Apply ordering if valid order_by is given
                if order_by in ['name', 'email']:
                    dataframe_df.sort_values(by=[order_by], ascending=True, inplace=True)

                if 'created_on' in dataframe_df.columns:
                    dataframe_df['created_on'] = dataframe_df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p') if pd.notna(x) else 'Invalid Date')
                else:
                    dataframe_df['created_on'] = ""

                dataframe_df.drop(columns=['profile_picture'], inplace=True)
                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)

                paginator = CambridgeDefaultPaginationClass()
                paginator.message = DATA_FOUND_SUCCESS
                result_page = paginator.paginate_queryset(json_list, request)
                return paginator.get_paginated_response(result_page)
            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))

    def retrieve(self, request, pk):
        queryset = UserMaster.objects.filter(id=pk).all().values('id',"full_name",'email','phone_number','user_role','country','is_active')
        if queryset:
            subadmin_list_dataframe = pd.DataFrame(queryset)
            subadmin_list_json = subadmin_list_dataframe.to_json(orient='records')
            subadmin_list_json = json.loads(subadmin_list_json)
            
            sub_admin_roles = MapRolesAccessToSubAdmin.objects.filter(user_id=pk,).all().values('id','access_id','access__access')
            sub_admin_roles_dataframe = pd.DataFrame(sub_admin_roles)
            sub_admin_roles_dataframe = sub_admin_roles_dataframe.rename(columns={'access__access':'access'}) 
            sub_admin_roles_json = sub_admin_roles_dataframe.to_json(orient='records')
            sub_admin_roles_json = json.loads(sub_admin_roles_json)

            if sub_admin_roles:
                subadmin_list_json[0]['access'] = sub_admin_roles_json
            else:
                subadmin_list_json[0]['access'] = []
            return http_200_response(message=FOUND,data=subadmin_list_json)  
        return http_200_response(message=NOT_FOUND)

    def destroy(self, request, pk=None):
        if pk:
            user = UserMaster.objects.filter(id=pk, is_deleted=False).last()
            if user:
                user.is_deleted=True
                user.save()
                return http_200_response(message=USER_DELETE)
            else:
                return http_400_response(message=NO_USER)
        else:
            return http_400_response(message=USER_ID)


    def update(self, request, pk ,*args, **kwargs):
        try:
            instance = UserMaster.objects.filter(id=int(pk)).last()
            if not instance:
                return http_400_response(message=NOT_FOUND)
            serialized_data = UpdateSubAdminSerializer(instance,request.data,context={'user':request.user,'request':request})
            if serialized_data.is_valid():
                return http_200_response(message=USER_UPDATE)
            else:
                if list(serialized_data.errors.keys())[0] != "error":
                    return http_400_response(message=f"{list(serialized_data.errors.keys())[0]} : {serialized_data.errors[list(serialized_data.errors.keys())[0]][0]}")
                else:
                    return http_400_response(message=serialized_data.errors[list(serialized_data.errors.keys())[0]][0])
        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))



### National head all api
class NationalHeadRegisterView(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get', 'post', 'put', 'delete']
    serializer_class = NationalHeadRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    # parser_classes = (FormParser, MultiPartParser)
 
    def get_serializer_class(self):
        if self.action == "create":
            return NationalHeadRegisterSerializer
        elif self.action == "retrieve":
            return GetNationalHeadSerializer
        elif self.action == "update":
            return UpdateNationalHeadSerializer
        else:
            return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,context={"request":request,})
        serializer.context['request'] = request  
        if serializer.is_valid():
            serializer.save()  
            return http_201_response(message="User created successfully")

        if list(serializer.errors.keys())[0] != "error":
                    return http_400_response(
                    message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}"
                )
        else:
            return http_400_response(message=serializer.errors[list(serializer.errors.keys())[0]][0])
        

    type_search = openapi.Parameter('search',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    # type_role = openapi.Parameter('role_id',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[type_search,type_status])
    def list(self,request):
        try:

            search = self.request.query_params.get('search')
            role_id = self.request.query_params.get('role_id')
            status = self.request.query_params.get('status')

            if role_id:
                queryset = UserMaster.objects.filter(user_role_id=role_id,is_deleted=False,is_active=True)
            else:
                queryset = UserMaster.objects.filter(user_role_id__in=[3,],is_deleted=False,is_active=True,created_by_id=request.user.id)

            
            queryset = queryset.values('id','employee_id','full_name','email','profile_picture','phone_number','user_role_id','user_role__role','address','description','is_active','created_on','assigned_by','assigned_by__full_name','created_by','created_by__full_name').order_by('-created_on')
            
            if status=="active":
                queryset=queryset.filter(is_active=True).all().order_by('-created_on')
            elif status=="inactive":
                queryset=queryset.filter(is_active=False).all().order_by('-created_on')
            else:
                queryset=queryset

            dataframe_df = pd.DataFrame((queryset))

            if not dataframe_df.empty:
            
                for index,row in dataframe_df.iterrows():
                    if dataframe_df.at[index,"profile_picture"]:
                        dataframe_df.at[index,"image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/"+str(dataframe_df.at[index,"profile_picture"])
                        # dataframe_df.at[index,"image"] = S3_BUCKET_BASE_URL+str(dataframe_df.at[index,"profile_picture"])

                    else:
                        dataframe_df.at[index,"image"] = ""

                dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

                # Check if 'id' column exists in dataframe_df
                if 'id' not in dataframe_df.columns:
                    return http_200_response(message=NOT_FOUND,data=[])

              
                if dataframe_df.empty:
                    return http_200_response(message=NOT_FOUND,data=[])

                ## rename
                dataframe_df.rename(columns={'role__role': 'role_name', 'bio': 'description', 'full_name': 'name',
                                            'state__name': 'state_name', 'city__name': 'city_name', 'phone_number': 'phone_number','assigned_by__full_name':'assigned_by_name','created_by__full_name':'created_by_name'}, inplace=True)
                if search:
                    search = search.strip()
                    search = re.escape(search)
                    dataframe_df = SearchUserRecord(dataframe_df, search)
                
                if 'created_on' in dataframe_df.columns:
                    dataframe_df['created_on'] = dataframe_df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p')if pd.notna(x) else 'Invalid Date')
                else:
                    dataframe_df['created_on'] = ""

                ## drop
                dataframe_df.drop(columns=['profile_picture'],inplace=True)

                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)
                paginator = CambridgeDefaultPaginationClass()
                paginator.message = DATA_FOUND_SUCCESS
                result_page = paginator.paginate_queryset(json_list, request)
                return paginator.get_paginated_response(result_page)
            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


    # def retrieve(self, request, pk=None):
    #     try:
    #         user_obj  = UserMaster.objects.filter(id=pk).last()

    #         outlet_data = GetNationalHeadSerializer(user_obj,context={'user':request.user,'request':request,'user_obj':user_obj}).data
    #         if outlet_data:
    #             return http_200_response(message=FOUND,data=outlet_data)
    #         else:
    #             return http_200_response(message=NOT_FOUND)
    #     except Exception as e:
    #         logException(e)
    #         return http_500_response(error=str(e))
        
    def retrieve(self, request, pk):
        queryset = UserMaster.objects.filter(id=pk).all().values('id',"full_name",'email','phone_number','user_role','country','is_active')
        if queryset:
            subadmin_list_dataframe = pd.DataFrame(queryset)
            subadmin_list_json = subadmin_list_dataframe.to_json(orient='records')
            subadmin_list_json = json.loads(subadmin_list_json)
            
            sub_admin_roles = MapRolesAccessToSubAdmin.objects.filter(user_id=pk).all().values('id','access_id','access__access')
            sub_admin_roles_dataframe = pd.DataFrame(sub_admin_roles)
            sub_admin_roles_dataframe = sub_admin_roles_dataframe.rename(columns={'access__access':'access'}) 
            sub_admin_roles_json = sub_admin_roles_dataframe.to_json(orient='records')
            sub_admin_roles_json = json.loads(sub_admin_roles_json)

            if sub_admin_roles:
                subadmin_list_json[0]['access'] = sub_admin_roles_json
            else:
                subadmin_list_json[0]['access'] = []
            return http_200_response(message=FOUND,data=subadmin_list_json)  
        return http_200_response(message=NOT_FOUND)

    def destroy(self, request, pk=None):
        if pk:
            user = UserMaster.objects.filter(id=pk, is_deleted=False).last()
            if user:
                user.is_deleted=True
                user.save()
                return http_200_response(message=USER_DELETE)
            else:
                return http_400_response(message=NO_USER)
        else:
            return http_400_response(message=USER_ID)


    def update(self, request, pk ,*args, **kwargs):
        try:
            instance = UserMaster.objects.filter(id=int(pk)).last()
            if not instance:
                return http_400_response(message=NOT_FOUND)
            serialized_data = UpdateNationalHeadSerializer(instance,request.data,context={'user':request.user,'request':request})
            if serialized_data.is_valid():
                return http_200_response(message=USER_UPDATE)
            else:
                if list(serialized_data.errors.keys())[0] != "error":
                    return http_400_response(message=f"{list(serialized_data.errors.keys())[0]} : {serialized_data.errors[list(serialized_data.errors.keys())[0]][0]}")
                else:
                    return http_400_response(message=serialized_data.errors[list(serialized_data.errors.keys())[0]][0])
        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))
        




### Sales head all api
class SalesRepresentativeRegisterView(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get', 'post', 'put', 'delete']
    serializer_class = SalesRepresentativeRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    # parser_classes = (FormParser, MultiPartParser)
 
    def get_serializer_class(self):
        if self.action == "create":
            return SalesRepresentativeRegisterSerializer
        elif self.action == "retrieve":
            return GetSalesRepresentativeSerializer
        elif self.action == "update":
            return UpdateSalesRepresentativeSerializer
        else:
            return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,context={"request":request,})
        serializer.context['request'] = request  
        if serializer.is_valid():
            serializer.save()  
            return http_201_response(message="User created successfully")

        if list(serializer.errors.keys())[0] != "error":
                    return http_400_response(
                    message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}"
                )
        else:
            return http_400_response(message=serializer.errors[list(serializer.errors.keys())[0]][0])
        

    type_search = openapi.Parameter('search',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    # type_role = openapi.Parameter('role_id',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[type_search,type_status])
    def list(self,request):
        try:

            search = self.request.query_params.get('search')
            role_id = self.request.query_params.get('role_id')
            status = self.request.query_params.get('status')

            if role_id:
                queryset = UserMaster.objects.filter(user_role_id=role_id,is_deleted=False,is_active=True)
            else:
                queryset = UserMaster.objects.filter(user_role_id__in=[5,],is_deleted=False,is_active=True,created_by_id=request.user.id)

            
            queryset = queryset.values('id','employee_id','full_name','email','profile_picture','phone_number','user_role_id','user_role__role','address','description','is_active','created_on','assigned_by','assigned_by__full_name','created_by','created_by__full_name').order_by('-created_on')
            
            if status=="active":
                queryset=queryset.filter(is_active=True).all().order_by('-created_on')
            elif status=="inactive":
                queryset=queryset.filter(is_active=False).all().order_by('-created_on')
            else:
                queryset=queryset

            dataframe_df = pd.DataFrame((queryset))

            if not dataframe_df.empty:
            
                for index,row in dataframe_df.iterrows():
                    if dataframe_df.at[index,"profile_picture"]:
                        dataframe_df.at[index,"image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/"+str(dataframe_df.at[index,"profile_picture"])
                        # dataframe_df.at[index,"image"] = S3_BUCKET_BASE_URL+str(dataframe_df.at[index,"profile_picture"])

                    else:
                        dataframe_df.at[index,"image"] = ""

                dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

                # Check if 'id' column exists in dataframe_df
                if 'id' not in dataframe_df.columns:
                    return http_200_response(message=NOT_FOUND,data=[])

              
                if dataframe_df.empty:
                    return http_200_response(message=NOT_FOUND,data=[])

                ## rename
                dataframe_df.rename(columns={'role__role': 'role_name', 'bio': 'description', 'full_name': 'name',
                                            'state__name': 'state_name', 'city__name': 'city_name', 'phone_number': 'phone_number','assigned_by__full_name':'assigned_by_name','created_by__full_name':'created_by_name'}, inplace=True)
                if search:
                    search = search.strip()
                    search = re.escape(search)
                    dataframe_df = SearchUserRecord(dataframe_df, search)
                
                if 'created_on' in dataframe_df.columns:
                    dataframe_df['created_on'] = dataframe_df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p')if pd.notna(x) else 'Invalid Date')
                else:
                    dataframe_df['created_on'] = ""

                ## drop
                dataframe_df.drop(columns=['profile_picture'],inplace=True)

                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)
                paginator = CambridgeDefaultPaginationClass()
                paginator.message = DATA_FOUND_SUCCESS
                result_page = paginator.paginate_queryset(json_list, request)
                return paginator.get_paginated_response(result_page)
            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


    def retrieve(self, request, pk=None):
        try:
            user_obj  = UserMaster.objects.filter(id=pk).last()
            outlet_data = GetSalesRepresentativeSerializer(user_obj,context={'user':request.user,'request':request,'user_obj':user_obj}).data
            if outlet_data:
                return http_200_response(message=FOUND,data=outlet_data)
            else:
                return http_200_response(message=NOT_FOUND)
        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))

    # def retrieve(self, request, pk):
    #     queryset = UserMaster.objects.filter(id=pk).all().values('id',"full_name",'email','phone_number','user_role','country','is_active')
    #     if queryset:
    #         subadmin_list_dataframe = pd.DataFrame(queryset)
    #         subadmin_list_json = subadmin_list_dataframe.to_json(orient='records')
    #         subadmin_list_json = json.loads(subadmin_list_json)
            
    #         sub_admin_roles = MapRolesAccessToSubAdmin.objects.filter(user_id=pk).all().values('id','access_id','access__access')
    #         sub_admin_roles_dataframe = pd.DataFrame(sub_admin_roles)
    #         sub_admin_roles_dataframe = sub_admin_roles_dataframe.rename(columns={'access__access':'access'}) 
    #         sub_admin_roles_json = sub_admin_roles_dataframe.to_json(orient='records')
    #         sub_admin_roles_json = json.loads(sub_admin_roles_json)

    #         if sub_admin_roles:
    #             subadmin_list_json[0]['access'] = sub_admin_roles_json
    #         else:
    #             subadmin_list_json[0]['access'] = []
    #         return http_200_response(message=FOUND,data=subadmin_list_json)  
    #     return http_200_response(message=NOT_FOUND)

    def destroy(self, request, pk=None):
        if pk:
            user = UserMaster.objects.filter(id=pk, is_deleted=False).last()
            if user:
                user.is_deleted=True
                user.save()
                return http_200_response(message=USER_DELETE)
            else:
                return http_400_response(message=NO_USER)
        else:
            return http_400_response(message=USER_ID)


    def update(self, request, pk ,*args, **kwargs):
        try:
            instance = UserMaster.objects.filter(id=int(pk)).last()
            if not instance:
                return http_400_response(message=NOT_FOUND)
            serialized_data = UpdateSalesRepresentativeSerializer(instance,request.data,context={'user':request.user,'request':request})
            if serialized_data.is_valid():
                return http_200_response(message=USER_UPDATE)
            else:
                if list(serialized_data.errors.keys())[0] != "error":
                    return http_400_response(message=f"{list(serialized_data.errors.keys())[0]} : {serialized_data.errors[list(serialized_data.errors.keys())[0]][0]}")
                else:
                    return http_400_response(message=serialized_data.errors[list(serialized_data.errors.keys())[0]][0])
        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))
        




### RegionalHead all api
class RegionalHeadRegisterView(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get', 'post', 'put', 'delete']
    serializer_class = RegionalHeadRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    # parser_classes = (FormParser, MultiPartParser)
 
    def get_serializer_class(self):
        if self.action == "create":
            return RegionalHeadRegisterSerializer
        elif self.action == "retrieve":
            return GetRegionalHeadSerializer
        elif self.action == "update":
            return UpdateRegionalHeadSerializer
        else:
            return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,context={"request":request,})
        serializer.context['request'] = request  
        if serializer.is_valid():
            serializer.save()  
            return http_201_response(message="User created successfully")

        if list(serializer.errors.keys())[0] != "error":
                    return http_400_response(
                    message=f"{list(serializer.errors.keys())[0]} : {serializer.errors[list(serializer.errors.keys())[0]][0]}"
                )
        else:
            return http_400_response(message=serializer.errors[list(serializer.errors.keys())[0]][0])
        

    type_search = openapi.Parameter('search',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    # type_role = openapi.Parameter('role_id',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[type_search,type_status])
    def list(self,request):
        try:

            search = self.request.query_params.get('search')
            role_id = self.request.query_params.get('role_id')
            status = self.request.query_params.get('status')

            if role_id:
                queryset = UserMaster.objects.filter(user_role_id=role_id,is_deleted=False,is_active=True)
            else:
                queryset = UserMaster.objects.filter(user_role_id__in=[4,],is_deleted=False,is_active=True,created_by_id=request.user.id)

            
            queryset = queryset.values('id','employee_id','full_name','email','profile_picture','phone_number','user_role_id','user_role__role','address','description','is_active','created_on','assigned_by','assigned_by__full_name','created_by','created_by__full_name','regional','regional__name').order_by('-created_on')
            
            if status=="active":
                queryset=queryset.filter(is_active=True).all().order_by('-created_on')
            elif status=="inactive":
                queryset=queryset.filter(is_active=False).all().order_by('-created_on')
            else:
                queryset=queryset

            dataframe_df = pd.DataFrame((queryset))

            if not dataframe_df.empty:
            
                for index,row in dataframe_df.iterrows():
                    if dataframe_df.at[index,"profile_picture"]:
                        dataframe_df.at[index,"image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/"+str(dataframe_df.at[index,"profile_picture"])
                        # dataframe_df.at[index,"image"] = S3_BUCKET_BASE_URL+str(dataframe_df.at[index,"profile_picture"])

                    else:
                        dataframe_df.at[index,"image"] = ""

                dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

                # Check if 'id' column exists in dataframe_df
                if 'id' not in dataframe_df.columns:
                    return http_200_response(message=NOT_FOUND,data=[])

              
                if dataframe_df.empty:
                    return http_200_response(message=NOT_FOUND,data=[])

                ## rename
                dataframe_df.rename(columns={'role__role': 'role_name', 'bio': 'description', 'full_name': 'name',
                                            'state__name': 'state_name', 'city__name': 'city_name', 'phone_number': 'phone_number','assigned_by__full_name':'assigned_by_name','created_by__full_name':'created_by_name','regional__name':'regional_name'}, inplace=True)
                if search:
                    search = search.strip()
                    search = re.escape(search)
                    dataframe_df = SearchUserRecord(dataframe_df, search)
                
                if 'created_on' in dataframe_df.columns:
                    dataframe_df['created_on'] = dataframe_df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p')if pd.notna(x) else 'Invalid Date')
                else:
                    dataframe_df['created_on'] = ""

                ## drop
                dataframe_df.drop(columns=['profile_picture'],inplace=True)

                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)
                paginator = CambridgeDefaultPaginationClass()
                paginator.message = DATA_FOUND_SUCCESS
                result_page = paginator.paginate_queryset(json_list, request)
                return paginator.get_paginated_response(result_page)
            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


    def retrieve(self, request, pk=None):
        try:
            user_obj  = UserMaster.objects.filter(id=pk).last()
            outlet_data = GetRegionalHeadSerializer(user_obj,context={'user':request.user,'request':request,'user_obj':user_obj}).data
            if outlet_data:
                return http_200_response(message=FOUND,data=outlet_data)
            else:
                return http_200_response(message=NOT_FOUND)
        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


    def destroy(self, request, pk=None):
        if pk:
            user = UserMaster.objects.filter(id=pk, is_deleted=False).last()
            if user:
                user.is_deleted=True
                user.save()
                return http_200_response(message=USER_DELETE)
            else:
                return http_400_response(message=NO_USER)
        else:
            return http_400_response(message=USER_ID)


    def update(self, request, pk ,*args, **kwargs):
        try:
            instance = UserMaster.objects.filter(id=int(pk)).last()
            if not instance:
                return http_400_response(message=NOT_FOUND)
            serialized_data = UpdateRegionalHeadSerializer(instance,request.data,context={'user':request.user,'request':request})
            if serialized_data.is_valid():
                return http_200_response(message=USER_UPDATE)
            else:
                if list(serialized_data.errors.keys())[0] != "error":
                    return http_400_response(message=f"{list(serialized_data.errors.keys())[0]} : {serialized_data.errors[list(serialized_data.errors.keys())[0]][0]}")
                else:
                    return http_400_response(message=serialized_data.errors[list(serialized_data.errors.keys())[0]][0])
        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))
        




        

# ### SubAdmin list api
class SubAdminUserListViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get',]
    serializer_class = SubAdminRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    parser_classes = (FormParser, MultiPartParser)

    def get_serializer_class(self):
        if self.action == "create":
            return SubAdminRegisterSerializer
        elif self.action == "retrieve":
            return GetSubAdminSerializer
        elif self.action == "update":
            return UpdateSubAdminSerializer
        else:
            return self.serializer_class

    type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_order_by = openapi.Parameter(
        'order_by',
        in_=openapi.IN_QUERY,
        type=openapi.TYPE_STRING,
        description="Sort by 'name', '-name', 'email', or '-email'"
    )

    @swagger_auto_schema(manual_parameters=[type_search, type_status, type_order_by])
    def list(self, request):
        try:
            search = self.request.query_params.get('search')
            status = self.request.query_params.get('status')
            order_by = self.request.query_params.get('order_by')

            role_id = request.user.user_role_id

            if role_id in [1]:
                queryset = UserMaster.objects.filter(user_role_id=2, is_deleted=False).order_by('-created_on')
            elif role_id == 2:
                queryset = UserMaster.objects.filter(is_deleted=False, id=request.user.id).order_by('-created_on')
            else:
                queryset = UserMaster.objects.none()

            dataframe_df = pd.DataFrame.from_records(queryset.values(
                'id', 'employee_id', 'full_name', 'email', 'phone_number', 'user_role_id', 
                'user_role__role', 'address', 'description', 'is_active', 'created_on', 
                'assigned_by', 'assigned_by__full_name','assigned_by__email', 'created_by', 'created_by__full_name'
            ))

            if dataframe_df.empty:
                return http_200_response(message=NOT_FOUND, data=[])

            dataframe_df.rename(columns={
                'user_role__role': 'role_name',
                'user_role_id': 'role_id',
                'bio': 'description',
                'full_name': 'name',
                'state__name': 'state_name',
                'city__name': 'city_name',
                'phone_number': 'phone_number',
                'assigned_by__full_name': 'assigned_by_name',
                'assigned_by__email': 'assigned_by_email',
                'created_by__full_name': 'created_by_name'
            }, inplace=True)

            dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)
            dataframe_df['created_on'] = dataframe_df['created_on'].apply(
                lambda x: x.strftime('%d-%m-%Y & %I:%M %p') if pd.notna(x) else ''
            )

            if status == "active":
                dataframe_df = dataframe_df[dataframe_df['is_active'] == True]
            elif status == "inactive":
                dataframe_df = dataframe_df[dataframe_df['is_active'] == False]

            if search:
                search = re.escape(search)
                dataframe_df = SearchUserRecord(dataframe_df, search)

            # ✅ Order by logic (support -name / -email)
            valid_fields = ['name', 'email','assigned_by_name','assigned_by_email','created_by_name']
            if order_by:
                ascending = True
                if order_by.startswith('-'):
                    ascending = False
                    order_by = order_by[1:]
                if order_by in valid_fields:
                    dataframe_df.sort_values(by=[order_by], ascending=ascending, inplace=True)

            json_list = dataframe_df.to_json(orient='records')
            json_list = json.loads(json_list)

            paginator = CambridgeDefaultPaginationClass()
            paginator.message = DATA_FOUND_SUCCESS
            result_page = paginator.paginate_queryset(json_list, request)
            return paginator.get_paginated_response(result_page)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


# ### Business list api

class BusinessUserListViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get',]
    serializer_class = SubAdminRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    parser_classes = (FormParser, MultiPartParser)

    def get_serializer_class(self):
        if self.action == "create":
            return SubAdminRegisterSerializer
        elif self.action == "retrieve":
            return GetSubAdminSerializer
        elif self.action == "update":
            return UpdateSubAdminSerializer
        else:
            return self.serializer_class

    type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_order_by = openapi.Parameter(
        'order_by', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING,
        description="Sort by 'name', '-name', 'email', or '-email'"
    )

    @swagger_auto_schema(manual_parameters=[type_search, type_status, type_order_by])
    def list(self, request):
        try:
            search = self.request.query_params.get('search')
            status = self.request.query_params.get('status')
            order_by = self.request.query_params.get('order_by')

            role_id = request.user.user_role_id

            if role_id == 1:
                queryset = UserMaster.objects.filter(user_role_id=3, is_deleted=False).order_by('-created_on')
            elif role_id == 2:
                queryset = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=3, is_deleted=False
                ).order_by('-created_on')
            elif role_id == 3:
                queryset = UserMaster.objects.filter(is_deleted=False, id=request.user.id).order_by('-created_on')
            else:
                queryset = UserMaster.objects.none()

            queryset = queryset.values(
                'id', 'employee_id', 'full_name', 'email', 'profile_picture', 'phone_number', 'user_role_id',
                'user_role__role', 'address', 'description', 'is_active', 'created_on', 'assigned_by',
                'assigned_by__full_name', 'assigned_by__email', 'created_by', 'created_by__full_name'
            ).order_by('-created_on')

            if status == "active":
                queryset = queryset.filter(is_active=True).order_by('-created_on')
            elif status == "inactive":
                queryset = queryset.filter(is_active=False).order_by('-created_on')

            dataframe_df = pd.DataFrame(queryset)

            if not dataframe_df.empty:
                for index, row in dataframe_df.iterrows():
                    profile_pic = dataframe_df.at[index, "profile_picture"]
                    if profile_pic:
                        dataframe_df.at[index, "image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/" + str(profile_pic)
                    else:
                        dataframe_df.at[index, "image"] = ""

                dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

                if 'id' not in dataframe_df.columns:
                    return http_200_response(message=NOT_FOUND, data=[])

                dataframe_df.rename(columns={
                    'user_role__role': 'role_name',
                    'user_role_id': 'role_id',
                    'bio': 'description',
                    'full_name': 'name',
                    'state__name': 'state_name',
                    'city__name': 'city_name',
                    'phone_number': 'phone_number',
                    'assigned_by__full_name': 'assigned_by_name',
                    'assigned_by__email': 'assigned_by_email',
                    'created_by__full_name': 'created_by_name'
                }, inplace=True)

                if search:
                    dataframe_df = dataframe_df[
                        (dataframe_df['name'].str.contains(search, case=False, na=False)) |
                        (dataframe_df['created_by_name'].str.contains(search, case=False, na=False)) |
                        (dataframe_df['employee_id'].str.contains(search, case=False, na=False)) |
                        (dataframe_df['assigned_by_name'].str.contains(search, case=False, na=False)) |
                        (dataframe_df['assigned_by_email'].str.contains(search, case=False, na=False)) |
                        (dataframe_df['phone_number'].str.contains(search, case=False, na=False)) |
                        (dataframe_df['email'].str.contains(search, case=False, na=False))
                    ]

                # ✅ Ordering support by 'name' or 'email' ascending or descending
                valid_fields = ['name', 'email']
                if order_by:
                    ascending = True
                    if order_by.startswith('-'):
                        ascending = False
                        order_by = order_by[1:]
                    if order_by in valid_fields:
                        dataframe_df.sort_values(by=[order_by], ascending=ascending, inplace=True)

                if 'created_on' in dataframe_df.columns:
                    dataframe_df['created_on'] = dataframe_df['created_on'].apply(
                        lambda x: x.strftime('%d-%m-%Y & %I:%M %p') if pd.notna(x) else 'Invalid Date'
                    )
                else:
                    dataframe_df['created_on'] = ""

                if 'profile_picture' in dataframe_df.columns:
                    dataframe_df.drop(columns=['profile_picture'], inplace=True)

                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)

                paginator = CambridgeDefaultPaginationClass()
                paginator.message = DATA_FOUND_SUCCESS
                result_page = paginator.paginate_queryset(json_list, request)
                return paginator.get_paginated_response(result_page)

            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))

# ### Regional list api

class RegionalUserListViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get',]
    serializer_class = SubAdminRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    parser_classes = (FormParser, MultiPartParser)

    type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_order_by = openapi.Parameter('order_by', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Sort by name or email, prefix with '-' for descending")

    @swagger_auto_schema(manual_parameters=[type_search, type_status, type_order_by])
    def list(self, request):
        try:
            search = self.request.query_params.get('search')
            status = self.request.query_params.get('status')
            order_by = self.request.query_params.get('order_by')

            role_id = request.user.user_role_id
            if role_id == 1:
                queryset = UserMaster.objects.filter(user_role_id=4, is_deleted=False).order_by('-created_on')
            elif role_id == 2:
                business_ids = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=3,
                    is_deleted=False
                ).values_list('id', flat=True)
                queryset = UserMaster.objects.filter(
                    Q(assigned_by_id__in=business_ids) | Q(created_by_id__in=business_ids) |
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=4,
                    is_deleted=False
                ).order_by('-created_on')
            elif role_id == 3:
                queryset = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=4,
                    is_deleted=False
                ).order_by('-created_on')
            elif role_id == 4:
                queryset = UserMaster.objects.filter(id=request.user.id, is_deleted=False).order_by('-created_on')
            else:
                queryset = UserMaster.objects.none()

            queryset = queryset.values(
                'id', 'employee_id', 'full_name', 'email', 'profile_picture', 'phone_number',
                'user_role_id', 'user_role__role', 'address', 'description', 'is_active', 'created_on',
                'assigned_by', 'assigned_by__full_name', 'assigned_by__email',
                'created_by', 'created_by__full_name','regional','regional__regional_name'
            )

            if status == "active":
                queryset = queryset.filter(is_active=True)
            elif status == "inactive":
                queryset = queryset.filter(is_active=False)

            dataframe_df = pd.DataFrame(list(queryset))

            if not dataframe_df.empty:
                for index, row in dataframe_df.iterrows():
                    if dataframe_df.at[index, "profile_picture"]:
                        dataframe_df.at[index, "image"] = str(request.build_absolute_uri('/'))[:-1] + "/media/" + str(dataframe_df.at[index, "profile_picture"])
                    else:
                        dataframe_df.at[index, "image"] = ""

                dataframe_df['employee_id'] = dataframe_df['employee_id'].fillna("").astype(str)

                dataframe_df.rename(columns={
                    'user_role__role': 'role_name',
                    'user_role_id': 'role_id',
                    'bio': 'description',
                    'full_name': 'name',
                    'state__name': 'state_name',
                    'city__name': 'city_name',
                    'phone_number': 'phone_number',
                    'assigned_by__full_name': 'assigned_by_name',
                    'assigned_by__email': 'assigned_by_email',
                    'created_by__full_name': 'created_by_name',
                    'regional__regional_name':'regional_name'
                }, inplace=True)

                if search:
                    dataframe_df = dataframe_df[
                        dataframe_df['name'].str.contains(search, case=False, na=False) |
                        dataframe_df['created_by_name'].str.contains(search, case=False, na=False) |
                        dataframe_df['employee_id'].str.contains(search, case=False, na=False) |
                        dataframe_df['assigned_by_name'].str.contains(search, case=False, na=False) |
                        dataframe_df['assigned_by_email'].str.contains(search, case=False, na=False) |
                        dataframe_df['phone_number'].str.contains(search, case=False, na=False) |
                        dataframe_df['email'].str.contains(search, case=False, na=False) |
                        dataframe_df['regional_name'].str.contains(search, case=False, na=False)
                    ]

                if 'created_on' in dataframe_df.columns:
                    dataframe_df['created_on'] = dataframe_df['created_on'].apply(
                        lambda x: x.strftime('%d-%m-%Y & %I:%M %p') if pd.notna(x) else 'Invalid Date'
                    )
                else:
                    dataframe_df['created_on'] = ""

                if 'profile_picture' in dataframe_df.columns:
                    dataframe_df.drop(columns=['profile_picture'], inplace=True)

                # Apply sorting
                if order_by in ['name', 'email']:
                    dataframe_df = dataframe_df.sort_values(by=order_by, ascending=True)
                elif order_by in ['-name', '-email']:
                    dataframe_df = dataframe_df.sort_values(by=order_by[1:], ascending=False)

                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)
                paginator = CambridgeDefaultPaginationClass()
                paginator.message = DATA_FOUND_SUCCESS
                result_page = paginator.paginate_queryset(json_list, request)
                return paginator.get_paginated_response(result_page)

            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))



def get_total_spent_time(sales_user_id):
        main_question_text = "Would you like to access a demo or speak with a representative for more details?"
        sub_question_text = "Yes, I’d like to explore a demo"
        print(sales_user_id,'111111111111111111111')
        # ✅ Find sub_question_ids where answer=True
        matching_feedbacks = BookFeedbackAnswerMapping.objects.filter(
            sub_question__sub_question=sub_question_text,
            sub_question__question__question=main_question_text,
            answer='True'
        )

        teacher_ids = matching_feedbacks.values_list('user_id', flat=True).distinct()
        # book_ids = matching_feedbacks.values_list('book_id', flat=True).distinct()
        print("teacher _id :------------=====",teacher_ids)

        return teacher_ids

        # # ✅ Sum watch time for matching teacher_ids
        # watch_time_data = UserBookReadMapping.objects.filter(user_id__in=teacher_ids,book_id__in = book_ids).aggregate(
        #     total_time=Sum('watch_time')
        # )

        # total_seconds = watch_time_data['total_time'] or 0

        # ✅ Convert to HH:MM:SS format
        # if total_seconds:
        #     total_seconds = int(total_seconds)
        #     hours, remainder = divmod(total_seconds, 3600)
        #     minutes, seconds = divmod(remainder, 60)
        #     return f"{hours:02}:{minutes:02}:{seconds:02}"
        # else:
        #     return "00:00:00"
        
# # # # dataframe used Sales user list api

# class SalesUserListViewset(ModelViewSet):
#     permission_classes = (IsAuthenticated,)
#     http_method_names = ['get']
#     pagination_class = CambridgeDefaultPaginationClass
#     queryset = UserMaster.objects.all().select_related("created_by", "assigned_by")
#     parser_classes = (FormParser, MultiPartParser)

#     type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
#     type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
#     type_order_by = openapi.Parameter('order_by', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Sort by name or email. Use -name or -email for descending order.")

#     @swagger_auto_schema(manual_parameters=[type_search, type_status, type_order_by])
#     def list(self, request):
#         try:
#             search = request.query_params.get('search')
#             status = request.query_params.get('status')
#             order_by = request.query_params.get('order_by')
#             role_id = request.user.user_role_id
#             base_filter = {'is_deleted': False}

#             user_filter = Q()
#             if role_id == 1:
#                 user_filter &= Q(user_role_id=5)
#             elif role_id == 2:
#                 business_ids = UserMaster.objects.filter(
#                     Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
#                     user_role_id=3, **base_filter
#                 ).values_list('id', flat=True)

#                 total_ids = UserMaster.objects.filter(
#                     Q(assigned_by_id__in=business_ids) | Q(created_by_id__in=business_ids),
#                     user_role_id=4, **base_filter
#                 ).values_list('id', flat=True)

#                 user_filter &= Q(
#                     Q(assigned_by_id__in=total_ids) | Q(created_by_id__in=total_ids) |
#                     Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
#                     user_role_id__in=[5, 6]
#                 )
#             elif role_id == 3:
#                 total_ids = UserMaster.objects.filter(
#                     Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
#                     user_role_id=4, **base_filter
#                 ).values_list('id', flat=True)

#                 user_filter &= Q(
#                     Q(assigned_by_id__in=total_ids) | Q(created_by_id__in=total_ids) |
#                     Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
#                     user_role_id__in=[5, 6]
#                 )
#             elif role_id == 4:
#                 user_filter &= Q(
#                     Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
#                     user_role_id__in=[5, 6]
#                 )
#             elif role_id == 5:
#                 user_filter &= Q(Q(id=request.user.id) | Q(created_by_id=request.user.id, user_role_id=6))
#             elif role_id == 6:
#                 user_filter &= Q(id=request.user.id)

#             queryset = UserMaster.objects.filter(user_filter, **base_filter).select_related("created_by", "assigned_by")

#             if status:
#                 queryset = queryset.filter(is_active=(status == "active"))

#             if search:
#                 queryset = queryset.filter(
#                     Q(full_name__icontains=search) |
#                     Q(created_by__full_name__icontains=search) |
#                     Q(employee_id__icontains=search) |
#                     Q(assigned_by__email__icontains=search) |
#                     Q(assigned_by__full_name__icontains=search) |
#                     Q(phone_number__icontains=search) |
#                     Q(email__icontains=search)
#                 )

#             df = pd.DataFrame(list(queryset.values(
#                 'id', 'employee_id', 'full_name', 'email', 'phone_number',
#                 'address', 'description', 'is_active', 'created_on',
#                 'created_by_id', 'assigned_by_id'
#             )))

#             user_map = {user.id: user for user in queryset}
#             qr_codes = {qr.user_id: qr for qr in QRCode.objects.filter(user_id__in=user_map.keys())}
#             base_url = request.build_absolute_uri(settings.MEDIA_URL)
#             if 'id' in df.columns:
#                 df['name'] = df['id'].map(lambda uid: user_map[uid].full_name if uid in user_map else "")
#                 df['created_by_name'] = df['id'].map(lambda uid: user_map[uid].created_by.full_name if user_map[uid].created_by else "")
#                 df['assigned_by_name'] = df['id'].map(lambda uid: user_map[uid].assigned_by.full_name if user_map[uid].assigned_by else "")
#                 df['assigned_by_email'] = df['id'].map(lambda uid: user_map[uid].assigned_by.email if user_map[uid].assigned_by else "")
#                 df['qr_code'] = df['id'].map(lambda uid: qr_codes[uid].qr_id if uid in qr_codes else "")
#                 df['qr_code_image'] = df['id'].map(lambda uid: f"{base_url}{qr_codes[uid].qr_code_image}" if uid in qr_codes else "")
                
#                 # df['qr_code_pdf_url'] = df['id'].map(lambda uid: generate_qr_pdf_views(qr_codes[uid], qr_codes[uid]) if uid in qr_codes else "")
#                 # df['total_lead_count']=UserMaster.objects.filter(user_role_id=6,)
#             else:
#                 df['name'] = ""
#                 df['created_by_name'] = ""
#                 df['assigned_by_name'] = ""
#                 df['assigned_by_email'] = ""
#                 df['qr_code'] = ""
#                 df['qr_code_image'] = ""
#                 # df['qr_code_pdf_url'] = ""
#                 # df['total_lead_count']=0

#             # Drop full_name column
#             if 'full_name' in df.columns:
#                 df.drop(columns=['full_name'], inplace=True)

#             # Handle sorting
#             if order_by in ['name', 'assigned_by_email', 'created_by_name', 'assigned_by_name']:
#                 df = df.sort_values(by=order_by, ascending=True)
#             elif order_by in ['-name', '-assigned_by_email', '-created_by_name', '-assigned_by_name']:
#                 df = df.sort_values(by=order_by[1:], ascending=False)

#             # Format created_on
#             if 'created_on' in df.columns:
#                 df['created_on'] = df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p') if pd.notna(x) else '')

#             # UTF-8 cleaning to prevent OverflowError
#             def safe_clean(val):
#                 try:
#                     return str(val).encode('utf-8', errors='ignore').decode('utf-8')
#                 except:
#                     return ""

#             for col in df.select_dtypes(include=['object']).columns:
#                 df[col] = df[col].map(safe_clean)

#             df = df.fillna("")
#             response_data = json.loads(df.to_json(orient='records', force_ascii=False))

#             page = self.paginate_queryset(response_data)
#             return self.get_paginated_response(page) if page else http_200_response(message=NOT_FOUND, data=[])

#         except Exception as e:
#             logException(e)
#             return http_500_response(error=str(e))


# new  dataframe used Sales user list api

class SalesUserListViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,)
    http_method_names = ['get']
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all().select_related("created_by", "assigned_by")
    parser_classes = (FormParser, MultiPartParser)

    type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_order_by = openapi.Parameter('order_by', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING, description="Sort by name or email. Use -name or -email for descending order.")

    @swagger_auto_schema(manual_parameters=[type_search, type_status, type_order_by])
    def list(self, request):
        try:
            search = request.query_params.get('search')
            status = request.query_params.get('status')
            order_by = request.query_params.get('order_by')
            role_id = request.user.user_role_id
            base_filter = {'is_deleted': False}

            user_filter = Q()
            if role_id == 1:
                user_filter &= Q(user_role_id=5)
            elif role_id == 2:
                business_ids = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=3, **base_filter
                ).values_list('id', flat=True)

                total_ids = UserMaster.objects.filter(
                    Q(assigned_by_id__in=business_ids) | Q(created_by_id__in=business_ids),
                    user_role_id=4, **base_filter
                ).values_list('id', flat=True)

                user_filter &= Q(
                    Q(assigned_by_id__in=total_ids) | Q(created_by_id__in=total_ids) |
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id__in=[5, 6]
                )
            elif role_id == 3:
                total_ids = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=4, **base_filter
                ).values_list('id', flat=True)

                user_filter &= Q(
                    Q(assigned_by_id__in=total_ids) | Q(created_by_id__in=total_ids) |
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id__in=[5, 6]
                )
            elif role_id == 4:
                user_filter &= Q(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id__in=[5, 6]
                )
            elif role_id == 5:
                user_filter &= Q(Q(id=request.user.id) | Q(created_by_id=request.user.id, user_role_id=6))
            elif role_id == 6:
                user_filter &= Q(id=request.user.id)

            queryset = UserMaster.objects.filter(user_filter, **base_filter).select_related("created_by", "assigned_by")

            if status:
                queryset = queryset.filter(is_active=(status == "active"))

            if search:
                queryset = queryset.filter(
                    Q(full_name__icontains=search) |
                    Q(created_by__full_name__icontains=search) |
                    Q(employee_id__icontains=search) |
                    Q(assigned_by__email__icontains=search) |
                    Q(assigned_by__full_name__icontains=search) |
                    Q(phone_number__icontains=search) |
                    Q(email__icontains=search)
                )

            df = pd.DataFrame(list(queryset.values(
                'id', 'employee_id', 'full_name', 'email', 'phone_number',
                'address', 'description', 'is_active', 'created_on',
                'created_by_id', 'assigned_by_id'
            )))

            user_map = {user.id: user for user in queryset}
            qr_codes = {qr.user_id: qr for qr in QRCode.objects.filter(user_id__in=user_map.keys())}
            base_url = request.build_absolute_uri(settings.MEDIA_URL)
            if 'id' in df.columns:
                df['name'] = df['id'].map(lambda uid: user_map[uid].full_name if uid in user_map else "")
                df['created_by_name'] = df['id'].map(lambda uid: user_map[uid].created_by.full_name if user_map[uid].created_by else "")
                df['assigned_by_name'] = df['id'].map(lambda uid: user_map[uid].assigned_by.full_name if user_map[uid].assigned_by else "")
                df['assigned_by_email'] = df['id'].map(lambda uid: user_map[uid].assigned_by.email if user_map[uid].assigned_by else "")
                df['qr_code'] = df['id'].map(lambda uid: qr_codes[uid].qr_id if uid in qr_codes else "")
                df['qr_code_image'] = df['id'].map(lambda uid: f"{base_url}{qr_codes[uid].qr_code_image}" if uid in qr_codes else "")
                
                # df['qr_code_pdf_url'] = df['id'].map(lambda uid: generate_qr_pdf_views(qr_codes[uid], qr_codes[uid]) if uid in qr_codes else "")

                main_question_text = "Would you like to access a demo or speak with a representative for more details?"
                sub_question_text = "Yes, I’d like to explore a demo"
                df['total_lead_count'] = df['id'].map(lambda uid: UserMaster.objects.filter(user_role_id=6,
                                            id__in=BookFeedbackAnswerMapping.objects.filter(
                                                sub_question__sub_question=sub_question_text,
                                                sub_question__question__question=main_question_text,
                                                answer='True'
                                            ).values_list('user_id', flat=True).distinct(),
                                            created_by_id=user_map[uid].id if uid in user_map else None
                                        ).count())
            else:
                df['name'] = ""
                df['created_by_name'] = ""
                df['assigned_by_name'] = ""
                df['assigned_by_email'] = ""
                df['qr_code'] = ""
                df['qr_code_image'] = ""
                # df['qr_code_pdf_url'] = ""
                df['total_lead_count']=0

            # Drop full_name column
            if 'full_name' in df.columns:
                df.drop(columns=['full_name'], inplace=True)

            # Handle sorting
            if order_by in ['name', 'assigned_by_email', 'created_by_name', 'assigned_by_name']:
                df = df.sort_values(by=order_by, ascending=True)
            elif order_by in ['-name', '-assigned_by_email', '-created_by_name', '-assigned_by_name']:
                df = df.sort_values(by=order_by[1:], ascending=False)

            # Format created_on
            if 'created_on' in df.columns:
                df['created_on'] = df['created_on'].apply(lambda x: x.strftime('%d-%m-%Y & %I:%M %p') if pd.notna(x) else '')

            # UTF-8 cleaning to prevent OverflowError
            def safe_clean(val):
                try:
                    return str(val).encode('utf-8', errors='ignore').decode('utf-8')
                except:
                    return ""

            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].map(safe_clean)

            df = df.fillna("")
            response_data = json.loads(df.to_json(orient='records', force_ascii=False))

            page = self.paginate_queryset(response_data)
            return self.get_paginated_response(page) if page else http_200_response(message=NOT_FOUND, data=[])

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))
        
# # # Teacher user list api

class TeacherUserListViewset(ModelViewSet):
    permission_classes = (IsAuthenticated,) 
    http_method_names = ['get',]
    serializer_class = SubAdminRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    parser_classes = (FormParser, MultiPartParser)

    # Swagger parameters
    type_search = openapi.Parameter('search', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_ordering = openapi.Parameter('order_by', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)

    @swagger_auto_schema(manual_parameters=[type_search, type_status, type_ordering])
    def list(self, request):
        try:
            search = request.query_params.get('search')
            status = request.query_params.get('status')
            order_by = request.query_params.get('order_by') or '-created_on'
            role_id = request.user.user_role_id

            if role_id == 1:
                queryset = UserMaster.objects.filter(user_role_id=6, is_deleted=False)
            elif role_id == 2:
                list_of_business_id = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=3, is_deleted=False,
                ).values_list('id', flat=True)
                list_of_rm_id = UserMaster.objects.filter(
                    Q(assigned_by_id__in=list_of_business_id) | Q(created_by_id__in=list_of_business_id),
                    user_role_id=4, is_deleted=False,
                ).values_list('id', flat=True)
                list_of_sales_id = UserMaster.objects.filter(
                    Q(assigned_by_id__in=list_of_rm_id) | Q(created_by_id__in=list_of_rm_id),
                    user_role_id=5, is_deleted=False,
                ).values_list('id', flat=True)
                queryset = UserMaster.objects.filter(
                    Q(created_by_id__in=list_of_sales_id) | Q(created_by_id=request.user.id),
                    user_role_id=6, is_deleted=False,
                )
            elif role_id == 3:
                list_of_rm_id = UserMaster.objects.filter(
                    Q(assigned_by_id=request.user.id) | Q(created_by_id=request.user.id),
                    user_role_id=4, is_deleted=False,
                ).values_list('id', flat=True)
                list_of_sales_id = UserMaster.objects.filter(
                    Q(assigned_by_id__in=list_of_rm_id) | Q(created_by_id__in=list_of_rm_id),
                    user_role_id=5, is_deleted=False,
                ).values_list('id', flat=True)
                queryset = UserMaster.objects.filter(
                    Q(created_by_id__in=list_of_sales_id) | Q(created_by_id=request.user.id),
                    user_role_id=6, is_deleted=False,
                )
            elif role_id == 4:
                list_of_sales_id = UserMaster.objects.filter(
                    user_role_id=5, is_deleted=False, created_by_id=request.user.id
                ).values_list('id', flat=True)
                queryset = UserMaster.objects.filter(
                    Q(created_by_id__in=list_of_sales_id) | Q(created_by_id=request.user.id),
                    user_role_id=6, is_deleted=False,
                )
            elif role_id == 5:
                queryset = UserMaster.objects.filter(
                    user_role_id=6, is_deleted=False, created_by_id=request.user.id
                )
            elif role_id == 6:
                queryset = UserMaster.objects.filter(
                    is_deleted=False, id=request.user.id
                )
            else:
                queryset = UserMaster.objects.none()

            queryset = queryset.values(
                'id', 'employee_id', 'full_name', 'email', 'phone_number',
                'user_role_id', 'user_role__role', 'address', 'description', 'is_active', 
                'created_on', 'assigned_by', 'assigned_by__full_name', 'assigned_by__email', 'created_by', 
                'created_by__full_name', 'board_id', 'board__name', 'school_id', 'school__name', 'country_id', 
                'country__name', 'state_id', 'state__name', 'city_id', 'city__name'
            )

            if status == "active":
                queryset = queryset.filter(is_active=True)
            elif status == "inactive":
                queryset = queryset.filter(is_active=False)

            if search:
                queryset = queryset.filter(
                    Q(full_name__icontains=search) | 
                    Q(created_by__full_name__icontains=search) | 
                    Q(employee_id__icontains=search) | 
                    Q(assigned_by__email__icontains=search) |
                    Q(assigned_by__full_name__icontains=search) | 
                    Q(phone_number__icontains=search) | 
                    Q(email__icontains=search) |
                    Q(board__name__icontains=search) |
                    Q(country__name__icontains=search) | 
                    Q(state__name__icontains=search) |
                    Q(school__name__icontains=search) |
                    Q(city__name__icontains=search)
                )

            data = list(queryset)

            subject_mappings = UserSubjectMapping.objects.filter(
                user_id__in=[user['id'] for user in data]
            ).values('user_id', 'subject_id', 'subject__name')

            user_subjects_map = defaultdict(list)
            for mapping in subject_mappings:
                user_subjects_map[mapping['user_id']].append({
                    "subject_id": mapping['subject_id'],
                    "subject_name": mapping['subject__name']
                })

            for user in data:
                user['assigned_by_name'] = user.pop('assigned_by__full_name', "") or ""
                user['assigned_by_email'] = user.pop('assigned_by__email', "") or ""
                user['created_by_name'] = user.pop('created_by__full_name', "") or ""
                user['role_id'] = user.pop('user_role_id', None)
                user['role_name'] = user.pop('user_role__role', "") or ""

                user['board_id'] = user.pop('board_id', None)
                user['school_id'] = user.pop('school_id', None)
                user['country_id'] = user.pop('country_id', None)
                user['state_id'] = user.pop('state_id', None)
                user['city_id'] = user.pop('city_id', None)

                user['board_name'] = user.pop('board__name', "") or ""
                user['school_name'] = user.pop('school__name', "") or ""
                user['country_name'] = user.pop('country__name', "") or ""
                user['state_name'] = user.pop('state__name', "") or ""
                user['city_name'] = user.pop('city__name', "") or ""

                user['subjects'] = user_subjects_map.get(user['id'], [])

            # Apply ordering if the field exists in the data
            if order_by.lstrip("-") in data[0].keys() if data else []:
                reverse = order_by.startswith("-")
                sort_key = order_by.lstrip("-")
                data.sort(key=lambda x: x.get(sort_key) or "", reverse=reverse)

            page = self.paginate_queryset(data)
            return self.get_paginated_response(page)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


# # Roles Access List      
  
class RoleAccessList(ModelViewSet):
    permission_classes = (IsAuthenticated, )
    http_method_names = ['get']

    role_type = openapi.Parameter('role_type',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[role_type,])
    def list(self, request, *args, **kwargs):
        role_type = self.request.query_params.get('role_type')
        # role_access = RoleAccessMaster.objects.all().order_by('id')
        #################
        role_id=self.request.user.user_role.id
        if role_id in [1,2,]:
            role_access = RoleAccessMaster.objects.all().order_by('id')
            if role_type:
                if int(role_type) == 1:
                    role_access = RoleAccessMaster.objects.all().order_by('id')
                if int(role_type) == 2:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 3:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 4:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 5:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[1, 15]).order_by('id')
        # elif role_id in [2,]:
        #     role_access = RoleAccessMaster.objects.all().order_by('id').exclude(id=15)
        #     if role_type:
        #         if int(role_type) == 1:
        #             role_access = RoleAccessMaster.objects.all().exclude(id__in=[1,]).order_by('id')
        #         if int(role_type) == 2:
        #             role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
        #         if int(role_type) == 3:
        #             role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
        #         if int(role_type) == 4:
        #             role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
        #         if int(role_type) == 5:
        #             role_access = RoleAccessMaster.objects.all().exclude(id__in=[1, 15]).order_by('id')
        elif role_id in [3,]:
            role_access = RoleAccessMaster.objects.all().order_by('id').exclude(id=15)
            if role_type:
                if int(role_type) == 1:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[1,]).order_by('id')
                if int(role_type) == 2:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 3:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 4:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 5:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[1, 15]).order_by('id')
        elif role_id in [4,]:
            role_access = RoleAccessMaster.objects.all().order_by('id').exclude(id=15)
            if role_type:
                if int(role_type) == 1:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[1,]).order_by('id')
                if int(role_type) == 2:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 3:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 4:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[15]).order_by('id')
                if int(role_type) == 5:
                    role_access = RoleAccessMaster.objects.all().exclude(id__in=[1, 15]).order_by('id')
        elif role_id in [5,]:
            role_access = RoleAccessMaster.objects.all().order_by('id').exclude(id__in=[1,15])
        #########################
        if role_access:
            serialized_data = RoleAccessListSerializer(role_access,many=True,context={"request":request,'role_type':role_type})
            return http_200_response(message=FOUND,data=serialized_data.data)
        else:
            return http_200_response(message=NOT_FOUND)
        


## role_access_status_list

class UserRoleAccessStatusViewsetFullyOptimized(ModelViewSet):
    permission_classes =(IsAuthenticated, )
    http_method_names = ['get']

    role_type = openapi.Parameter('role_type',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    user_id = openapi.Parameter('user_id',in_= openapi.IN_QUERY, type = openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[user_id,role_type])
    def list(self,request):
      try:
        user_id = request.query_params.get('user_id')
        user_id = int(user_id) if user_id is not None else 0
        role_type = request.query_params.get('role_type')
        if not user_id:
          return http_400_response(message="Please provide valid user id")
    
        user = UserMaster.objects.filter(id= int(user_id)).last()
        # role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
        ##############
        role_id=self.request.user.user_role.id
        if role_id in [1,]:
            role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
            submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
            if role_type:
                if int(role_type) in [1,]:
                    role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
                    submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
                if int(role_type) == 2:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 3:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 4:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2,3]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)

                if int(role_type) == 5:

                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[1, 15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1, 2, 3, 4]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)

        elif role_id in [2,]:
            role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
            submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id=1).values("id",'name','role_access_id'))
            if role_type:
                if int(role_type) == 1:
                    role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
                    submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
                if int(role_type) == 2:
                    role_access_qs = RoleAccessMaster.objects.objects.all().order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 3:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 4:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2,3]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                    
                if int(role_type) == 5:

                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[1, 15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1, 2, 3, 4]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
        elif role_id in [3,]:
            role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
            submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,]).values("id",'name','role_access_id'))
            if role_type:
                if int(role_type) == 1:
                    role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
                    submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
                if int(role_type) == 2:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 3:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 4:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2,3]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                    
                if int(role_type) == 5:

                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[1, 15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1, 2, 3, 4]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
        elif role_id in [4,]:
            role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
            submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,3]).values("id",'name','role_access_id'))
            if role_type:
                if int(role_type) == 1:
                    role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
                    submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
                if int(role_type) == 2:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 3:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                if int(role_type) == 4:
                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1,2,3]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
                    
                if int(role_type) == 5:

                    role_access_qs = RoleAccessMaster.objects.exclude(id__in=[1, 15]).order_by('id').values("id", "access")
                    role_access_df = pd.DataFrame(role_access_qs)

                    submodule_qs = SubModuleMaster.objects.exclude(id__in=[1, 2, 3, 4]).values("id", "name", "role_access_id")
                    submodule_df = pd.DataFrame(submodule_qs)
        elif role_id in [5,]:
            role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id__in=[1,15]).values("id","access"))
            submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,3,4,]).values("id",'name','role_access_id'))
        #####################
        # submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id=1).values("id",'name','role_access_id'))
        submodule_crud_df = pd.DataFrame(SubModuleCRUDMaster.objects.all().values("id",'name','submodule_access_id',"role_access_id"))
        # user_access_df = pd.DataFrame(MapRolesAccessToSubAdmin.objects.filter(user_id = user.id).all().values("id","access_id","submodule_access_id","submodule_crud_access_id"))
        if user:
            user_access_df = pd.DataFrame(MapRolesAccessToSubAdmin.objects.filter(user_id=user.id).values("id", "access_id", "submodule_access_id", "submodule_crud_access_id"))
        else:
            user_access_df = pd.DataFrame()
        result=[]
        access_data = pd.DataFrame()
        if len(role_access_df)>0:
          for index,row in role_access_df.iterrows():
              #OuterMost - Parent Access Details
              role_access_data = dict()
              role_access_data['id'] = role_access_df.at[index,'id']
              role_access_data['access'] = role_access_df.at[index,"access"]

              #Now checking submodules access data
              submodules = submodule_df.loc[(submodule_df["role_access_id"] == role_access_df.at[index,'id'])]
              submodule_result = []
              submodule_status = pd.DataFrame()
              if len(submodules)>0:
                  for submodule_index,row in submodules.iterrows():
                      #First Level Nested data for submodule access data
                      submodule_data = dict()
                      submodule_data['id'] = submodules.at[submodule_index,'id']
                      submodule_data['name'] = submodules.at[submodule_index,'name']

                      #Now checking submodule crud data
                      submodule_cruds = submodule_crud_df.loc[(submodule_crud_df['submodule_access_id'] == submodules.at[submodule_index,'id'])]
                      sub_module_crud_result = []
                      submodule_crud_status = pd.DataFrame()
                      if len(submodule_cruds)>0:
                          for submodule_crud_index,row in submodule_cruds.iterrows():
                              sub_module_crud_data = dict()
                              sub_module_crud_data['id'] = submodule_cruds.at[submodule_crud_index,'id']
                              sub_module_crud_data['name'] = submodule_cruds.at[submodule_crud_index,'name']
                              if len(user_access_df)>0:
                                submodule_crud_status = user_access_df.loc[(user_access_df['submodule_crud_access_id'] == submodule_cruds.at[submodule_crud_index,"id"])]
                              if user.user_role_id in [2,3,4,5]:
                                if len(submodule_crud_status)>0:
                                    sub_module_crud_data['status']=True
                                else:
                                    sub_module_crud_data['status']=False
                              else:
                                    sub_module_crud_data['status']=True
                              sub_module_crud_result.append(sub_module_crud_data)
                          submodule_data['sub_module_crud'] = sub_module_crud_result
                      else:
                          submodule_data['sub_module_crud'] = None
                      if len(user_access_df)>0:
                        submodule_status = user_access_df.loc[(user_access_df['submodule_access_id'] == submodules.at[submodule_index,"id"])]
                      if user.user_role_id in [2,3,4,5]:
                          if len(submodule_status)>0:
                              submodule_data["status"]=True
                          else:
                              submodule_data["status"]=False
                      else:
                          submodule_data["status"]=True
                      submodule_result.append(submodule_data)
                      sub_module_cruds_result=None
              else:
                  sub_module_cruds = submodule_crud_df.loc[(submodule_crud_df['role_access_id'] == role_access_df.at[index,'id'])]
                  sub_module_cruds_result = []
                  if len(sub_module_cruds)>0:
                    for submodule_crud_index,row in sub_module_cruds.iterrows():
                      sub_module_crud_data = dict()
                      sub_module_crud_data['id'] = sub_module_cruds.at[submodule_crud_index,'id']
                      sub_module_crud_data['name'] = sub_module_cruds.at[submodule_crud_index,'name']
                      if len(user_access_df)>0:
                        submodule_crud_status = user_access_df.loc[(user_access_df['submodule_crud_access_id'] == sub_module_cruds.at[submodule_crud_index,"id"])]
                      if user.user_role_id in [2,3,4,5]:
                        if len(submodule_crud_status)>0:
                            sub_module_crud_data['status']=True
                        else:
                            sub_module_crud_data['status']=False
                      else:
                            sub_module_crud_data['status']=True
                      sub_module_cruds_result.append(sub_module_crud_data)
                  else:
                      sub_module_cruds_result=None
              role_access_data["sub_module"] = submodule_result
              role_access_data['sub_module_crud'] = sub_module_cruds_result
              if len(user_access_df)>0:
                access_data = user_access_df.loc[(user_access_df['access_id'] == role_access_df.at[index,"id"])]
              if user.user_role_id in [2,3,4,5]:
                  if len(access_data)>0:
                      role_access_data['status'] = True
                  else:
                      role_access_data['status'] = False
              else:
                  role_access_data['status'] = True
              
              result.append(role_access_data)
        return http_200_response(message="Data found successfully.",data= result)

      except Exception as e:
          return http_500_response(error=str(e))



# # new role access status list
# class UserRoleAccessStatusViewsetFullyOptimized(ModelViewSet):
#     permission_classes = (IsAuthenticated,)
#     http_method_names = ['get']

#     role_type = openapi.Parameter('role_type', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
#     user_id = openapi.Parameter('user_id', in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)

#     @swagger_auto_schema(manual_parameters=[user_id, role_type])
#     def list(self, request):
#         user_id = request.query_params.get('user_id')
#         role_type = request.query_params.get('role_type')

#         if not user_id or not user_id.isdigit():
#             return http_400_response(message="Please provide a valid user id")

#         user_id = int(user_id)
#         user = UserMaster.objects.filter(id=user_id).last()
#         if not user:
#             return http_400_response(message="User not found")

#         role_id = request.user.user_role.id
#         role_access_qs = RoleAccessMaster.objects.all().order_by('id')
#         submodule_qs = SubModuleMaster.objects.all()

#         if role_id == 1:
#             if role_type and role_type.isdigit():
#                 exclusions = {2: [15], 3: [15], 4: [15], 5: [1, 15]}.get(int(role_type), [])
#                 role_access_qs = role_access_qs.exclude(id__in=exclusions)

#                 sub_exclusions = {2: [1], 3: [1, 2], 4: [1, 2, 3], 5: [1, 2, 3, 4]}.get(int(role_type), [])
#                 submodule_qs = submodule_qs.exclude(id__in=sub_exclusions)
        
#         role_access_df = pd.DataFrame(role_access_qs.values("id", "access"))
#         submodule_df = pd.DataFrame(submodule_qs.values("id", "name", "role_access_id"))
#         submodule_crud_df = pd.DataFrame(SubModuleCRUDMaster.objects.all().values("id", "name", "submodule_access_id", "role_access_id"))
#         user_access_df = pd.DataFrame(MapRolesAccessToSubAdmin.objects.filter(user_id=user.id).values("id", "access_id", "submodule_access_id", "submodule_crud_access_id")) if user else pd.DataFrame()

#         result = []
#         for index, row in role_access_df.iterrows():
#             role_access_data = {"id": row['id'], "access": row["access"], "sub_module": [], "sub_module_crud": None}
            
#             submodules = submodule_df[submodule_df["role_access_id"] == row['id']]
#             for _, sub_row in submodules.iterrows():
#                 submodule_data = {"id": sub_row['id'], "name": sub_row['name'], "sub_module_crud": []}
                
#                 submodule_cruds = submodule_crud_df[submodule_crud_df['submodule_access_id'] == sub_row['id']]
#                 for _, crud_row in submodule_cruds.iterrows():
#                     submodule_crud_status = user_access_df[user_access_df['submodule_crud_access_id'] == crud_row['id']] if not user_access_df.empty else pd.DataFrame()
#                     submodule_data['sub_module_crud'].append({
#                         "id": crud_row['id'], "name": crud_row['name'],
#                         "status": len(submodule_crud_status) > 0 if role_id in [2, 3, 4, 5] else True
#                     })
                
#                 submodule_status = user_access_df[user_access_df['submodule_access_id'] == sub_row['id']] if not user_access_df.empty else pd.DataFrame()
#                 submodule_data["status"] = len(submodule_status) > 0 if role_id in [2, 3, 4, 5] else True
#                 role_access_data["sub_module"].append(submodule_data)
            
#             role_access_status = user_access_df[user_access_df['access_id'] == row['id']] if not user_access_df.empty else pd.DataFrame()
#             role_access_data['status'] = len(role_access_status) > 0 if role_id in [2, 3, 4, 5] else True
#             result.append(role_access_data)

#         return http_200_response(message="Data found successfully.", data=result)


# ## All Drop down user list api

class UserDropdownListViewset(ModelViewSet):
    # permission_classes = (IsAuthenticated,) 
    http_method_names = ['get',]
    serializer_class = SubAdminRegisterSerializer
    pagination_class = CambridgeDefaultPaginationClass
    queryset = UserMaster.objects.all()
    parser_classes = (FormParser, MultiPartParser)
 
    def get_serializer_class(self):
        if self.action == "create":
            return SubAdminRegisterSerializer
        elif self.action == "retrieve":
            return GetSubAdminSerializer
        elif self.action == "update":
            return UpdateSubAdminSerializer
        else:
            return self.serializer_class

        

    type_search = openapi.Parameter('search',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_role = openapi.Parameter('role_id',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    type_status = openapi.Parameter('status',in_=openapi.IN_QUERY, type=openapi.TYPE_STRING)
    @swagger_auto_schema(manual_parameters=[type_search,type_role,type_status])
    def list(self,request):
        try:

            search = self.request.query_params.get('search')
            role_id = self.request.query_params.get('role_id')
            status = self.request.query_params.get('status')
            if request.user.user_role_id in [1,2]:
                if role_id:
                    queryset = UserMaster.objects.filter(user_role_id=role_id,is_deleted=False)
            elif request.user.user_role_id in [3]:
                if role_id == "3":
                    queryset = UserMaster.objects.filter(user_role_id=role_id,id= request.user.id,is_deleted=False)
                if role_id == "4":
                    queryset = UserMaster.objects.filter(user_role_id=role_id,assigned_by_id = request.user.id,is_deleted=False)
            elif request.user.user_role_id in [4]:
                if role_id == "4":
                    queryset = UserMaster.objects.filter(user_role_id=role_id,id= request.user.id,is_deleted=False)          


            # else:
            #     queryset = UserMaster.objects.filter(user_role_id__in=[1,2,3,4,5,6],is_deleted=False,)

            
            queryset = queryset.values('id','full_name',).order_by('-created_on')
            
            if status=="active":
                queryset=queryset.filter(is_active=True).all().order_by('-created_on')
            elif status=="inactive":
                queryset=queryset.filter(is_active=False).all().order_by('-created_on')
            else:
                queryset=queryset

            dataframe_df = pd.DataFrame((queryset))

            if not dataframe_df.empty:

                if dataframe_df.empty:
                    return http_200_response(message=NOT_FOUND,data=[])

                if search:
                    search = search.strip()
                    search = re.escape(search)
                    dataframe_df = SearchUserRecord(dataframe_df, search)

                dataframe_df = dataframe_df.fillna("")
                json_list = dataframe_df.to_json(orient='records')
                json_list = json.loads(json_list)
                return http_200_response_pagination(message=FOUND,data=json_list)
            else:
                return http_200_response_pagination(message=NOT_FOUND)

        except Exception as e:
            logException(e)
            return http_500_response(error=str(e))


 ## new  dashboard get_user_role_access

# class GetUserRoleAccessViewsetFullyOptimized(ModelViewSet):
#     #################################
#   permission_classes = (IsAuthenticated, )
#   http_method_names = ['get']
#   def list(self, request, *args, **kwargs):
#     try:
#       user = request.user
#     #   role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
#       ##############
#       role_id=self.request.user.user_role.id
#       if role_id in [1,]:
#         role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
#         submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
#       elif role_id in [2,]:
#         role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
#         submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id=1).values("id",'name','role_access_id'))
#       elif role_id in [3,]:
#         role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
#         submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,]).values("id",'name','role_access_id'))
#       elif role_id in [4,]:
#         role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
#         submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,3]).values("id",'name','role_access_id'))
#       elif role_id in [5,]:
#         role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id__in=[1,15]).values("id","access"))
#         submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,3,4,]).values("id",'name','role_access_id'))
#         #####################
#     #   submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
#       submodule_crud_df = pd.DataFrame(SubModuleCRUDMaster.objects.all().values("id",'name','submodule_access_id',"role_access_id"))
#       user_access_df = pd.DataFrame(MapRolesAccessToSubAdmin.objects.filter(user_id = user.id).all().values("id","access_id","submodule_access_id","submodule_crud_access_id"))
#       result=[]
#       access_data = pd.DataFrame()
#       result.append({"id": 20,"title": "Dashboard","sub_module": [],"status": True})
      
#       if len(role_access_df)>0:
#         for index,row in role_access_df.iterrows():
#             #OuterMost - Parent Access Details
#             role_access_data = dict()
#             role_access_data['id'] = role_access_df.at[index,'id']
#             role_access_data['title'] = role_access_df.at[index,"access"]

#             #Now checking submodules access data
#             submodules = submodule_df.loc[(submodule_df["role_access_id"] == role_access_df.at[index,'id'])]
#             submodule_result = []
#             submodule_status = pd.DataFrame()
#             if len(submodules)>0:
#                 for submodule_index,row in submodules.iterrows():
#                     #First Level Nested data for submodule access data
#                     submodule_data = dict()
#                     submodule_data['id'] = submodules.at[submodule_index,'id']
#                     submodule_data['name'] = submodules.at[submodule_index,'name']

#                     #Now checking submodule crud data
#                     submodule_cruds = submodule_crud_df.loc[(submodule_crud_df['submodule_access_id'] == submodules.at[submodule_index,'id'])]
#                     sub_module_crud_result = []
#                     submodule_crud_status = pd.DataFrame()
#                     if len(submodule_cruds)>0:
#                         for submodule_crud_index,row in submodule_cruds.iterrows():
#                             sub_module_crud_data = dict()
#                             sub_module_crud_data['id'] = submodule_cruds.at[submodule_crud_index,'id']
#                             sub_module_crud_data['name'] = submodule_cruds.at[submodule_crud_index,'name']
#                             if len(user_access_df)>0:
#                               submodule_crud_status = user_access_df.loc[(user_access_df['submodule_crud_access_id'] == submodule_cruds.at[submodule_crud_index,"id"])]
#                             if user.user_role_id in [2,3,4,5]:
#                               if len(submodule_crud_status)>0:
#                                   sub_module_crud_data['status']=True
#                               else:
#                                   sub_module_crud_data['status']=False
#                             else:
#                                   sub_module_crud_data['status']=True
#                             sub_module_crud_result.append(sub_module_crud_data)
#                         submodule_data['sub_module_crud'] = sub_module_crud_result
#                     else:
#                         submodule_data['sub_module_crud'] = None
#                     if len(user_access_df)>0:
#                       submodule_status = user_access_df.loc[(user_access_df['submodule_access_id'] == submodules.at[submodule_index,"id"])]
#                     if user.user_role_id in [2,3,4,5]:
#                         if len(submodule_status)>0:
#                             submodule_data["status"]=True
#                         else:
#                             submodule_data["status"]=False
#                     else:
#                         submodule_data["status"]=True
#                     submodule_result.append(submodule_data)
#                     sub_module_cruds_result=None
#             else:
#                 sub_module_cruds = submodule_crud_df.loc[(submodule_crud_df['role_access_id'] == role_access_df.at[index,'id'])]
#                 sub_module_cruds_result = []
#                 if len(sub_module_cruds)>0:
#                   for submodule_crud_index,row in sub_module_cruds.iterrows():
#                     sub_module_crud_data = dict()
#                     sub_module_crud_data['id'] = sub_module_cruds.at[submodule_crud_index,'id']
#                     sub_module_crud_data['name'] = sub_module_cruds.at[submodule_crud_index,'name']
#                     if len(user_access_df)>0:
#                       submodule_crud_status = user_access_df.loc[(user_access_df['submodule_crud_access_id'] == sub_module_cruds.at[submodule_crud_index,"id"])]
#                     if user.user_role_id in [2,3,4,5]:
#                       if len(submodule_crud_status)>0:
#                           sub_module_crud_data['status']=True
#                       else:
#                           sub_module_crud_data['status']=False
#                     else:
#                           sub_module_crud_data['status']=True
#                     sub_module_cruds_result.append(sub_module_crud_data)
#                 else:
#                     sub_module_cruds_result=None
#             role_access_data["sub_module"] = submodule_result
#             role_access_data['sub_module_crud'] = sub_module_cruds_result
#             if len(user_access_df)>0:
#               access_data = user_access_df.loc[(user_access_df['access_id'] == role_access_df.at[index,"id"])]
#             if user.user_role_id in [2,3,4,5]:
#                 if len(access_data)>0:
#                     role_access_data['status'] = True
#                 else:
#                     role_access_data['status'] = False
#             else:
#                 role_access_data['status'] = True
            
#             result.append(role_access_data)
#       return http_200_response(message="Data found successfully.",data= result)

#     except Exception as e:
#         return http_500_response(error=str(e))



# new  get_user_role_access usedr dashboard api
class GetUserRoleAccessViewsetFullyOptimized(ModelViewSet):
    #################################
  permission_classes = (IsAuthenticated, )
  http_method_names = ['get']
  def list(self, request, *args, **kwargs):
    try:
      user = request.user
    #   role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
      ##############
      role_id=self.request.user.user_role.id
    #   if role_id in [1,]:
      if role_id in [1,2]:
        role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
        submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
      if role_id in [2,]:
        role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').values("id","access"))
        submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id=1).values("id",'name','role_access_id'))
      elif role_id in [3,]:
        role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
        submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2]).values("id",'name','role_access_id'))
      elif role_id in [4,]:
        role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id=15).values("id","access"))
        submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,3]).values("id",'name','role_access_id'))
      elif role_id in [5,]:
        role_access_df = pd.DataFrame(RoleAccessMaster.objects.all().order_by('id').exclude(id__in=[1,15]).values("id","access"))
        submodule_df = pd.DataFrame(SubModuleMaster.objects.all().exclude(id__in=[1,2,3,4]).values("id",'name','role_access_id'))
        #####################
    #   submodule_df = pd.DataFrame(SubModuleMaster.objects.all().values("id",'name','role_access_id'))
      submodule_crud_df = pd.DataFrame(SubModuleCRUDMaster.objects.all().values("id",'name','submodule_access_id',"role_access_id"))
      user_access_df = pd.DataFrame(MapRolesAccessToSubAdmin.objects.filter(user_id = user.id).all().values("id","access_id","submodule_access_id","submodule_crud_access_id"))
      result=[]
      access_data = pd.DataFrame()
      result.append({"id": 20,"title": "Dashboard","sub_module": [],"status": True})
      
      if len(role_access_df)>0:
        for index,row in role_access_df.iterrows():
            #OuterMost - Parent Access Details
            role_access_data = dict()
            role_access_data['id'] = role_access_df.at[index,'id']
            role_access_data['title'] = role_access_df.at[index,"access"]

            #Now checking submodules access data
            submodules = submodule_df.loc[(submodule_df["role_access_id"] == role_access_df.at[index,'id'])]
            submodule_result = []
            submodule_status = pd.DataFrame()
            if len(submodules)>0:
                for submodule_index,row in submodules.iterrows():
                    #First Level Nested data for submodule access data
                    submodule_data = dict()
                    submodule_data['id'] = submodules.at[submodule_index,'id']
                    submodule_data['name'] = submodules.at[submodule_index,'name']

                    #Now checking submodule crud data
                    submodule_cruds = submodule_crud_df.loc[(submodule_crud_df['submodule_access_id'] == submodules.at[submodule_index,'id'])]
                    sub_module_crud_result = []
                    submodule_crud_status = pd.DataFrame()
                    if len(submodule_cruds)>0:
                        for submodule_crud_index,row in submodule_cruds.iterrows():
                            sub_module_crud_data = dict()
                            sub_module_crud_data['id'] = submodule_cruds.at[submodule_crud_index,'id']
                            sub_module_crud_data['name'] = submodule_cruds.at[submodule_crud_index,'name']
                            if len(user_access_df)>0:
                              submodule_crud_status = user_access_df.loc[(user_access_df['submodule_crud_access_id'] == submodule_cruds.at[submodule_crud_index,"id"])]
                            if user.user_role_id in [2,3,4,5]:
                              if len(submodule_crud_status)>0:
                                  sub_module_crud_data['status']=True
                              else:
                                  sub_module_crud_data['status']=False
                            else:
                                  sub_module_crud_data['status']=True
                            sub_module_crud_result.append(sub_module_crud_data)
                        submodule_data['sub_module_crud'] = sub_module_crud_result
                    else:
                        submodule_data['sub_module_crud'] = None
                    if len(user_access_df)>0:
                      submodule_status = user_access_df.loc[(user_access_df['submodule_access_id'] == submodules.at[submodule_index,"id"])]
                    if user.user_role_id in [2,3,4,5]:
                        if len(submodule_status)>0:
                            submodule_data["status"]=True
                        else:
                            submodule_data["status"]=False
                    else:
                        submodule_data["status"]=True
                    submodule_result.append(submodule_data)
                    sub_module_cruds_result=None
            else:
                sub_module_cruds = submodule_crud_df.loc[(submodule_crud_df['role_access_id'] == role_access_df.at[index,'id'])]
                sub_module_cruds_result = []
                if len(sub_module_cruds)>0:
                  for submodule_crud_index,row in sub_module_cruds.iterrows():
                    sub_module_crud_data = dict()
                    sub_module_crud_data['id'] = sub_module_cruds.at[submodule_crud_index,'id']
                    sub_module_crud_data['name'] = sub_module_cruds.at[submodule_crud_index,'name']
                    if len(user_access_df)>0:
                      submodule_crud_status = user_access_df.loc[(user_access_df['submodule_crud_access_id'] == sub_module_cruds.at[submodule_crud_index,"id"])]
                    if user.user_role_id in [2,3,4,5]:
                      if len(submodule_crud_status)>0:
                          sub_module_crud_data['status']=True
                      else:
                          sub_module_crud_data['status']=False
                    else:
                          sub_module_crud_data['status']=True
                    sub_module_cruds_result.append(sub_module_crud_data)
                else:
                    sub_module_cruds_result=None
            role_access_data["sub_module"] = submodule_result
            role_access_data['sub_module_crud'] = sub_module_cruds_result
            if len(user_access_df)>0:
              access_data = user_access_df.loc[(user_access_df['access_id'] == role_access_df.at[index,"id"])]
            if user.user_role_id in [2,3,4,5]:
                if len(access_data)>0:
                    role_access_data['status'] = True
                else:
                    role_access_data['status'] = False
            else:
                role_access_data['status'] = True
            
            result.append(role_access_data)
      return http_200_response(message="Data found successfully.",data= result)

    except Exception as e:
        return http_500_response(error=str(e))
