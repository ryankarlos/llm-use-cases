"""Tests for Bedrock Agent management using moto.

Moto supports bedrock-agent for creating/managing agents and knowledge bases,
but NOT bedrock-agent-runtime (invoke_agent). So these tests cover the
management/provisioning side, not the runtime invocation.

Supported moto bedrock-agent operations:
- create_agent, get_agent, list_agents, delete_agent
- create_knowledge_base, get_knowledge_base, list_knowledge_bases, delete_knowledge_base
- tag_resource, untag_resource, list_tags_for_resource
"""

import os
import sys

import boto3
import pytest
from moto import mock_aws

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def bedrock_agent_client(aws_credentials):
    """Create mock Bedrock Agent client."""
    with mock_aws():
        client = boto3.client("bedrock-agent", region_name="us-east-1")
        yield client


@pytest.fixture
def iam_role(aws_credentials):
    """Create a mock IAM role for Bedrock agents."""
    with mock_aws():
        iam = boto3.client("iam", region_name="us-east-1")
        
        # Create role
        role = iam.create_role(
            RoleName="test-bedrock-agent-role",
            AssumeRolePolicyDocument="""{
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }]
            }"""
        )
        
        yield role["Role"]["Arn"]


class TestBedrockAgentCreation:
    """Tests for Bedrock Agent creation using moto."""
    
    def test_create_agent(self, aws_credentials):
        """Test creating a Bedrock agent."""
        with mock_aws():
            # Create IAM role first
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-agent-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            role_arn = role["Role"]["Arn"]
            
            # Create agent (instruction must be >= 40 chars)
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            response = client.create_agent(
                agentName="test-booking-agent",
                agentResourceRoleArn=role_arn,
                foundationModel="amazon.nova-lite-v1:0",
                instruction="You are a test booking assistant that helps patients book appointments."
            )
            
            assert "agent" in response
            assert response["agent"]["agentName"] == "test-booking-agent"
            assert response["agent"]["agentStatus"] in ["CREATING", "NOT_PREPARED", "PREPARED"]
    
    def test_get_agent(self, aws_credentials):
        """Test retrieving a Bedrock agent."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-agent-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            create_response = client.create_agent(
                agentName="test-agent",
                agentResourceRoleArn=role["Role"]["Arn"],
                foundationModel="amazon.nova-lite-v1:0",
                instruction="This is a test instruction that must be at least forty characters long."
            )
            
            agent_id = create_response["agent"]["agentId"]
            
            # Get the agent
            get_response = client.get_agent(agentId=agent_id)
            
            assert get_response["agent"]["agentId"] == agent_id
            assert get_response["agent"]["agentName"] == "test-agent"
    
    def test_list_agents(self, aws_credentials):
        """Test listing Bedrock agents."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-agent-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            
            # Create multiple agents
            for i in range(3):
                client.create_agent(
                    agentName=f"test-agent-{i}",
                    agentResourceRoleArn=role["Role"]["Arn"],
                    foundationModel="amazon.nova-lite-v1:0",
                    instruction=f"Test instruction number {i} that must be at least forty characters."
                )
            
            # List agents
            response = client.list_agents()
            
            assert "agentSummaries" in response
            assert len(response["agentSummaries"]) == 3
    
    def test_delete_agent(self, aws_credentials):
        """Test deleting a Bedrock agent."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-agent-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            create_response = client.create_agent(
                agentName="agent-to-delete",
                agentResourceRoleArn=role["Role"]["Arn"],
                foundationModel="amazon.nova-lite-v1:0",
                instruction="This agent will be deleted after creation for testing purposes."
            )
            
            agent_id = create_response["agent"]["agentId"]
            
            # Delete the agent
            delete_response = client.delete_agent(agentId=agent_id)
            
            assert delete_response["agentId"] == agent_id
            assert delete_response["agentStatus"] == "DELETING"
            
            # Verify it's gone from list
            list_response = client.list_agents()
            agent_ids = [a["agentId"] for a in list_response["agentSummaries"]]
            assert agent_id not in agent_ids


class TestBedrockKnowledgeBase:
    """Tests for Bedrock Knowledge Base using moto."""
    
    def test_create_knowledge_base(self, aws_credentials):
        """Test creating a knowledge base."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-kb-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            response = client.create_knowledge_base(
                name="test-nhs-kb",
                roleArn=role["Role"]["Arn"],
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
                    }
                },
                storageConfiguration={
                    "type": "OPENSEARCH_SERVERLESS",
                    "opensearchServerlessConfiguration": {
                        "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/test",
                        "vectorIndexName": "test-index",
                        "fieldMapping": {
                            "vectorField": "embedding",
                            "textField": "text",
                            "metadataField": "metadata"
                        }
                    }
                }
            )
            
            assert "knowledgeBase" in response
            assert response["knowledgeBase"]["name"] == "test-nhs-kb"
    
    def test_get_knowledge_base(self, aws_credentials):
        """Test retrieving a knowledge base."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-kb-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            create_response = client.create_knowledge_base(
                name="test-kb",
                roleArn=role["Role"]["Arn"],
                knowledgeBaseConfiguration={
                    "type": "VECTOR",
                    "vectorKnowledgeBaseConfiguration": {
                        "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
                    }
                },
                storageConfiguration={
                    "type": "OPENSEARCH_SERVERLESS",
                    "opensearchServerlessConfiguration": {
                        "collectionArn": "arn:aws:aoss:us-east-1:123456789012:collection/test",
                        "vectorIndexName": "test-index",
                        "fieldMapping": {
                            "vectorField": "embedding",
                            "textField": "text",
                            "metadataField": "metadata"
                        }
                    }
                }
            )
            
            kb_id = create_response["knowledgeBase"]["knowledgeBaseId"]
            
            # Get the knowledge base
            get_response = client.get_knowledge_base(knowledgeBaseId=kb_id)
            
            assert get_response["knowledgeBase"]["knowledgeBaseId"] == kb_id
            assert get_response["knowledgeBase"]["name"] == "test-kb"
    
    def test_list_knowledge_bases(self, aws_credentials):
        """Test listing knowledge bases."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-kb-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            
            # Create multiple KBs
            for i in range(2):
                client.create_knowledge_base(
                    name=f"test-kb-{i}",
                    roleArn=role["Role"]["Arn"],
                    knowledgeBaseConfiguration={
                        "type": "VECTOR",
                        "vectorKnowledgeBaseConfiguration": {
                            "embeddingModelArn": "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
                        }
                    },
                    storageConfiguration={
                        "type": "OPENSEARCH_SERVERLESS",
                        "opensearchServerlessConfiguration": {
                            "collectionArn": f"arn:aws:aoss:us-east-1:123456789012:collection/test-{i}",
                            "vectorIndexName": "test-index",
                            "fieldMapping": {
                                "vectorField": "embedding",
                                "textField": "text",
                                "metadataField": "metadata"
                            }
                        }
                    }
                )
            
            # List KBs
            response = client.list_knowledge_bases()
            
            assert "knowledgeBaseSummaries" in response
            assert len(response["knowledgeBaseSummaries"]) == 2


class TestBedrockTagging:
    """Tests for Bedrock resource tagging using moto."""
    
    def test_tag_agent(self, aws_credentials):
        """Test tagging a Bedrock agent."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-agent-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            create_response = client.create_agent(
                agentName="tagged-agent",
                agentResourceRoleArn=role["Role"]["Arn"],
                foundationModel="amazon.nova-lite-v1:0",
                instruction="This is a tagged agent for testing tagging functionality."
            )
            
            agent_arn = create_response["agent"]["agentArn"]
            
            # Tag the agent
            client.tag_resource(
                resourceArn=agent_arn,
                tags={"Environment": "test", "Project": "nhs-booking"}
            )
            
            # List tags
            tags_response = client.list_tags_for_resource(resourceArn=agent_arn)
            
            assert tags_response["tags"]["Environment"] == "test"
            assert tags_response["tags"]["Project"] == "nhs-booking"
    
    def test_untag_agent(self, aws_credentials):
        """Test removing tags from a Bedrock agent."""
        with mock_aws():
            iam = boto3.client("iam", region_name="us-east-1")
            role = iam.create_role(
                RoleName="test-agent-role",
                AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[]}'
            )
            
            client = boto3.client("bedrock-agent", region_name="us-east-1")
            create_response = client.create_agent(
                agentName="tagged-agent",
                agentResourceRoleArn=role["Role"]["Arn"],
                foundationModel="amazon.nova-lite-v1:0",
                instruction="This is a tagged agent for testing untagging functionality."
            )
            
            agent_arn = create_response["agent"]["agentArn"]
            
            # Add tags
            client.tag_resource(
                resourceArn=agent_arn,
                tags={"ToRemove": "yes", "ToKeep": "yes"}
            )
            
            # Remove one tag
            client.untag_resource(
                resourceArn=agent_arn,
                tagKeys=["ToRemove"]
            )
            
            # Verify
            tags_response = client.list_tags_for_resource(resourceArn=agent_arn)
            
            assert "ToRemove" not in tags_response["tags"]
            assert tags_response["tags"]["ToKeep"] == "yes"
