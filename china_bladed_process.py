from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.amazon.aws.operators.batch import BatchOperator
from airflow.providers.amazon.aws.operators.lambda_function import LambdaInvokeFunctionOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator

# 设置DAG的默认参数
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 21),
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
}

# 创建DAG
dag = DAG(
    'china_bladed_process_dag',
    default_args=default_args,
)

start_task = DummyOperator(task_id='start_task', dag=dag)
end_task = DummyOperator(task_id='end_task', dag=dag)

JOB_OVERRIDES = {}

# 定义变量
lambda_function_name_create_lustre = 'create_lustre' # 步骤3.8创建的Lambda函数名字
lambda_function_name_delete_lustre = 'delete_lustre' # 步骤3.7创建的Lambda函数名字
payload = '{"key1": "value1", "key2": "value2"}'

# 定义LambdaInvokeFunctionOperator
lambda_task_create_lustre = LambdaInvokeFunctionOperator(
    task_id='invoke_lambda_task_create_lustre',
    function_name=lambda_function_name_create_lustre,
    invocation_type='RequestResponse',
    payload=payload,
    dag=dag,
)

lambda_task_delete_lustre = LambdaInvokeFunctionOperator(
    task_id='invoke_lambda_task_delete_lustre',
    function_name=lambda_function_name_delete_lustre,
    invocation_type='RequestResponse',
    payload=payload,
    dag=dag,
)

# 定义BashOperator
bash_task = BashOperator(
    task_id='bash_task',
    bash_command='sleep 600',
    dag=dag,
)

# 定义后处理BatchOperator
submit_batch_job_postprocess = BatchOperator(
    task_id='submit_batch_job_postprocess',
    job_name='batch_job_name_postprocess',
    job_queue='postprocess-airflow-bladed-getting-started-wizard-job-queue', # 步骤3.5创建的Job queue
    job_definition='postprocess-airflow-bladed-getting-started-wizard-job-definition:3', # 步骤3.5创建的Job definition
    overrides=JOB_OVERRIDES,
    dag=dag,
)

for i in range(30):
    # 定义前处理BatchOperator
    submit_batch_job = BatchOperator(
        task_id='submit_batch_job_'+str(i),
        job_name='batch_job_name_'+str(i),
        job_queue='airflow-bladed-getting-started-wizard-job-queue',
        job_definition='airflow-bladed-getting-started-wizard-job-definition:2',
        overrides=JOB_OVERRIDES,
        dag=dag,
    )

    start_task >> submit_batch_job >> lambda_task_create_lustre >> bash_task >> submit_batch_job_postprocess >> lambda_task_delete_lustre >> end_task