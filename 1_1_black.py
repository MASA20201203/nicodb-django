import os

import boto3


def sum(a, b):
    """aとbを足す"""
    return a + b


def show_doc():
    """この関数のドキュメントを表示"""
    print(boto3.__doc__)
    print(os.__doc__)
