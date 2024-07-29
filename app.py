import boto3
import streamlit as st
import datetime
import json
import streamlit as st
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("--environmentName", type=str, default=None)
parser.add_argument("--codeS3Bucket", type=str, default=None)

args = parser.parse_args()

environmentName = args.environmentName
bucket_name = args.codeS3Bucket

boto3_session = boto3.session.Session()
region_name = boto3_session.region_name
# s3_client = boto3_session.client('s3')
ssm_client = boto3_session.client('ssm')
response = ssm_client.get_parameter(Name=f'/streamlitapp/{environmentName}/DataSourceId')
DataSourceId = response['Parameter']['Value']
response = ssm_client.get_parameter(Name=f'/streamlitapp/{environmentName}/KnowledgeBaseId')
KnowledgeBaseId = response['Parameter']['Value']
bedrock_client = boto3.client('bedrock-agent')

datasource = bedrock_client.get_data_source(
    dataSourceId= DataSourceId,
    knowledgeBaseId=KnowledgeBaseId
)

s3_bucket_arn = datasource['dataSource']['dataSourceConfiguration']['s3Configuration']['bucketArn']
s3_bucket_name = s3_bucket_arn.split(':')[-1]

s3 = boto3_session.resource('s3')

file_bucket = s3.Bucket(s3_bucket_name)
list_of_files = []
for file_bucket_object in file_bucket.objects.all():
    list_of_files.append(file_bucket_object.key)

st.subheader('Chat with On Premises Data', divider='orange')
st.markdown(f"<span style='color:gray'> This is a chatbot for asking questions using Amazon Bedrock about AWS S3 , OSS , Amazon Bedrock.The application uses the  pdf files of user guides of the AWS services to represent On Premises Files migrated to Amazon S3 using Amazon S3 File Gateway </span>", unsafe_allow_html=True)

with st.sidebar:
    #st.image('images/arch.png', caption='On Prem data for GenAI Apps' ,width =  500)
    
    #st.subheader('', divider='orange')
    #st.subheader('')
    #st.subheader('')
    with st.expander("Files", expanded = True):
        if len(list_of_files) == 0:
            st.write('No Files are present')
        else:
            st.write(str(list_of_files))

    # cfn_launch_oss = f'https://{region_name}.console.aws.amazon.com/cloudformation/home?region={region_name}#/stacks/create?stackName=on-prem-oss-kb&templateURL=https://{bucket_name}.s3.amazonaws.com/templates/main.yaml'

    with st.expander("Admin", expanded = True):
        st.write('''
            Provision S3 file gateway for on Premises
            data
        ''')
        #gateway_setup = f'https://github.com/mitrsudiaws/s3-file-gateway-to-amazon-bedrock-for-rag-with-onprem-data/blob/main/GATEWAY.md'

        st.write("check out this [link](https://github.com/mitrsudiaws/s3-file-gateway-to-amazon-bedrock-for-rag-with-onprem-data/blob/main/GATEWAY.md)")
        # st.link_button("Step 1. Create S3 File Gateway for On Prem Data", cfn_launch_s3gw ,help="Deploys S3 File gateway to connect to On Premises data")
    
    st.subheader('', divider='orange')
    st.subheader('')
    st.subheader('')

    with st.expander("Chat User Instructions", expanded = True):
        st.write('''
            1. Ask a question before any files have being loaded
               The application will not find any relevant answer.
            2. Ask a question after files have been loaded.It 
               may take a few minutes for the load to complete.
               You can see the list of files available to ask 
               questions.                
               The Application will show relevant answers.
            ''')

  

    # st.link_button("Step 1. Create Knowledge Base",cfn_launch_oss ,help="Deploys OSS Vector Database , Index")
    # st.subheader('')
    # st.subheader('')
    

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

for message in st.session_state.chat_history:
    with st.chat_message(message['role']):
        st.markdown(message['text'])


bedrockClient = boto3.client('bedrock-agent-runtime', region_name)

def getAnswers(questions):
    ssm_client = boto3_session.client('ssm')
    response = ssm_client.get_parameter(Name=f'/streamlitapp/{environmentName}/KnowledgeBaseId')
    KnowledgeBaseId = response['Parameter']['Value']

    knowledgeBaseResponse  = bedrockClient.retrieve_and_generate(
        input={'text': questions},
        retrieveAndGenerateConfiguration={
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': KnowledgeBaseId,
                'modelArn': f'arn:aws:bedrock:{region_name}::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
            },
            'type': 'KNOWLEDGE_BASE'
        })
    return knowledgeBaseResponse


questions = st.chat_input('Enter your questions here...')
#st.write("Step 2. Start asking questions")

#and (searchchoice == "Internal Documents")
if questions :
    with st.chat_message('user'):
        st.markdown(questions)
    st.session_state.chat_history.append({"role":'user', "text":questions})
    print(questions)
    response = getAnswers(questions)
    # st.write(response)
    answer = response['output']['text']

    with st.chat_message('assistant'):
        st.markdown(answer)
    st.session_state.chat_history.append({"role":'assistant', "text": answer})

    try:
        if len(response['citations'][0]['retrievedReferences']) == 0:
            st.markdown(f"<span style='color:blue'>Information is not present in the files</span>", unsafe_allow_html=True)
        
        elif len(response['citations'][0]['retrievedReferences']) != 0:
        
            context = response['citations'][0]['retrievedReferences'][0]['content']['text']
            doc_url = response['citations'][0]['retrievedReferences'][0]['location']['s3Location']['uri']
        
        #Below lines are used to show the context and the document source for the latest Question Answer
        #st.markdown(f"<span style='color:#FFDA33'>Context used: </span>{context}", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#FFDA33'>Source Document: </span>{doc_url}", unsafe_allow_html=True)
    
    except Exception as e:
        st.markdown(f"<span style='color:blue'>Information is not present in the files</span>", unsafe_allow_html=True)