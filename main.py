import argparse
import logging

import boto3
import docker
import watchtower


def run_docker(image, command, logger):
    client = docker.from_env()
    docker_run_options = {
        "detach": True,
        "remove": True,
        "stdout": True,
        "stderr": True,
        "stream": True,
        "command": command,
    }
    container = client.containers.run(image, **docker_run_options)  # docker run
    container.exec_run(command, detach=True)
    logger.info(f"Command: {command}")
    try:
        for line in container.logs(stream=True):
            logger.info(line.strip())
    except Exception as e:
        logger.error("Error processing logs:", str(e))
    finally:
        container.stop()
        logger.info("Container stopped and removed.")


def aws_setup_logs(log_group_name, log_stream_name, region_name, access_key, secret_key):
    boto3_client = boto3.client(
        "logs",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name
    )
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    handler = watchtower.CloudWatchLogHandler(
        boto3_client=boto3_client,
        log_group_name=log_group_name,
        log_stream_name=log_stream_name
    )
    logger.addHandler(handler)
    return logger, boto3_client


def parse_args():
    parser = argparse.ArgumentParser(description="Run Docker and log to AWS CloudWatch.")
    parser.add_argument("--docker-image", required=True, help="Name of the Docker image.")
    parser.add_argument("--bash-command", required=True, help="Bash command to run inside the Docker.")
    parser.add_argument("--aws-cloudwatch-group", required=True, help="AWS CloudWatch log group name.")
    parser.add_argument("--aws-cloudwatch-stream", required=True, help="AWS CloudWatch log stream name.")
    parser.add_argument("--aws-access-key-id", required=True, help="AWS access key ID.")
    parser.add_argument("--aws-secret-access-key", required=True, help="AWS secret access key.")
    parser.add_argument("--aws-region", required=True, help="AWS region.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    logger, aws_client = aws_setup_logs(
        args.aws_cloudwatch_group,
        args.aws_cloudwatch_stream,
        args.aws_region,
        args.aws_access_key_id,
        args.aws_secret_access_key,
    )
    run_docker(args.docker_image, args.bash_command, logger)
