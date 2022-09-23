#!/bin/bash
# Setup script for CentOS
yum install -y java-1.8.0-openjdk.x86_64
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-7.9.2-x86_64.rpm
rpm -ivh elasticsearch-7.9.2-x86_64.rpm
systemctl enable elasticsearch.service

rm elasticsearch-7.9.2-x86_64.rpm

{
    echo 'node.name: "SDX Node1"'
    echo 'cluster.name: sdxcluster1'
} >> /etc/elasticsearch/elasticsearch.yml

service elasticsearch start