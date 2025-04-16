from rest_framework.response import Response
from rest_framework import status


# Common Response
def http_200_response(message,error="",data=""):
    context={
        "status":True,
        "status_code":200,
        "message":message,
        "error":error,
        'data':data
        }
    
    return Response(context,status=status.HTTP_200_OK)
 
def http_200_response_pagination(message,error="",data=""):
    context={
        "status":True,
        "status_code":200,
        "message":message,
        "error":error,
        'data':data
        }
    return Response(context,status=status.HTTP_200_OK) 

 
def http_500_response(error=None,message="",data=""):
    context={
        "status":False,
        "status_code":500,
        "message":"Something Went Wrong!",
        "error":error,
        "data":data
 
        }
    return Response(context,status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def http_201_response(message,error="",data=""):
    context={
        "status":True,
        "status_code":201,
        "message":message,
        "error":error,
        "data":data
        }
    return Response(context,status=status.HTTP_201_CREATED)
 
 
def http_400_response(message,error="",data=""):
    context={
        "status":False,
        "status_code":400,
        "message":message,
        "error":error,
        "data":data
 
        }
    return Response(context,status=status.HTTP_400_BAD_REQUEST)


def http_200_response_false_response(message,error="",data=None):
    context={
        "status":False,
        "status_code":200,
        "message":message,
        "error":error,
        'data':data
        }
    return Response(context,status=status.HTTP_200_OK)




def http_200_response_pagination(message, error="", data=""):

    context = {
        "status": True,
        "status_code": 200,
        "message": message,
        "error": error,
        "data": data,
    }
    return Response(context, status=status.HTTP_200_OK)


def http_200_response_pagination_app(message, error="", data=None):

    context = {
        "status": True,
        "status_code": 200,
        "message": message,
        "error": error,
        "data": data,
    }
    return Response(context, status=status.HTTP_200_OK)
    
def http_200_response_pagination_false(message, error="", data=[]):

    context = {
        "status": True,
        "status_code": 200,
        "message": message,
        "error": error,
        "data": data,
    }
    return Response(context, status=status.HTTP_200_OK)