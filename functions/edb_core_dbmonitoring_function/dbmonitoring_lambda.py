""" Function to filter the RDS CloudWatch logs and then store it in S3 bucket in CSV format
"""
#pylint: disable=R0914
from datetime import datetime,timedelta
import time
import csv
import boto3
def lambda_handler(event, context):  #pylint: disable=W0613
    """ Function to filter the RDS CloudWatch logs and then store it in S3 bucket in CSV format
    """
    client = boto3.client('logs')
    s3_resource=boto3.resource('s3')
    bucket_name='edp-sec'
    cur_date=datetime.now().strftime('%y-%m-%d')
    key=str(cur_date)+'.csv'
    bucket=s3_resource.Bucket(bucket_name)
    t_diff_inhrs=24
    log_group_names=[]
    config={'MaxItems': 50,'PageSize': 50}
    paginator = client.get_paginator('describe_log_groups')
    for page in paginator.paginate(logGroupNamePrefix='/aws/rds',PaginationConfig=config):
        for group in page['logGroups']:
            log_group_names.append(group['logGroupName'])
    query = " fields @timestamp as Timestamp " + \
            "| parse @message 'UTC:*(' as clientIP " + \
            "| parse @message '(*)' as Port " + \
            "| parse @message '):*@*:[*]:' as UserName , DatabaseName, ProcessId " + \
            "| parse @message 'connection *:'as Connection " + \
            "| parse @message 'password authentication * for' as Authentication " + \
            "| filter Connection ='authorized' " + \
            "OR Authentication='failed' OR Connection='received' " + \
            "| sort @timestamp desc "
    lg_group=[log_group_names[i:i+5] for i in range(0, len(log_group_names), 5)]
    query_id=[]
    now=datetime.now()
    strtime=int((now-timedelta(hours=t_diff_inhrs)).timestamp())

    for sub_log_group in lg_group:
        for single_log_group in sub_log_group:
            #print(single_log_group)
            start_query_response = client.start_query(
                                                        logGroupName=single_log_group,
                                                        startTime=strtime,
                                                        endTime=int(datetime.now().timestamp()),
                                                        queryString=query,
                                                    )
            query_id .append( start_query_response['queryId'] )
    q_map=dict(zip(query_id,log_group_names))
    df_data=[]
    for q_id in query_id:
        response = None
        while response is None or response['status'] == 'Running': # pylint: disable=unsubscriptable-object
            #print('Waiting for query to complete ...')
            time.sleep(1)
            response = client.get_query_results(queryId=q_id)
        for res in response['results']:
            df1_data=[]
            for r_res in res:
                if r_res['field']!="@ptr":
                    df1_data.append(r_res['value'])
            df1_data.append(q_map[f'{q_id}'])
            df_data.append(df1_data)
            print(q_map[f'{q_id}'])
    df_data.reverse()
    # local_file_name='/tmp/logs.csv'
    # write the data into '/tmp' folder
    with open('/tmp/logs.csv', 'w', newline='\n', encoding="utf-8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(['TimeStamp',
                         'ClientIP',
                         'PortNo',
                         'UserName',
                         'DataBaseName',
                         'ServiceID',
                         'Connection',
                         'LogGroupName'])
        for line in df_data:
            writer.writerow(line)
    # upload the temp folder
    bucket.upload_file('/tmp/logs.csv',f'database_monitoring/{key}')
    