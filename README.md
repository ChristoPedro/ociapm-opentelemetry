# Enviando dados apra o OCI APM através OpenTelemetry Collector

Esse tutorial tem como objetivo mostrar como instalar e configurar o OpenTelemetry Operator para enviar métricas para o **APM** (Application Performance Monitoring) da Oracle Cloud.

## Conteúdo

- [Enviando dados apra o OCI APM através OpenTelemetry Collector](#enviando-dados-apra-o-oci-apm-através-opentelemetry-collector)
  - [Conteúdo](#conteúdo)
  - [Instalando o Operator](#instalando-o-operator)
    - [Pré-requisitos](#pré-requisitos)
    - [Instalação](#instalação)
  - [Criando um APM Domain](#criando-um-apm-domain)
  - [Obtendo as informações necessárias do APM Domain](#obtendo-as-informações-necessárias-do-apm-domain)
    - [Data Upload Endpoint](#data-upload-endpoint)
    - [Data Keys](#data-keys)
  - [Criando um OpenTelemetry Collector](#criando-um-opentelemetry-collector)
  - [Testando a configuração](#testando-a-configuração)
    - [Primeiro Teste](#primeiro-teste)



## Instalando o Operator

### Pré-requisitos

Para a instalação do Operador do OpenTelemetry para Kubernetes, é preciso ter o Cert-Manager instalado.

> Veja a documentação do [**Cert-Manager**](https://cert-manager.io/docs/installation/) 

Pode ser instalado através do comando baixo:

```kubectl 
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.11.0/cert-manager.yaml 
```
 Se tiver um **OKE** (Oracle Kubernetes Engine) Ehenced Cluster no OCI é possível adicionar através dos Add-ons. Documentação [aqui](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengconfiguringclusteraddons.htm#contengconfiguringclusteraddons).

### Instalação

Para instalar o Operator para Kubernetes basta executar o comando abaixo:

```kubectl
$ kubectl apply -f https://github.com/open-telemetry/opentelemetry-operator/releases/latest/download/opentelemetry-operator.yaml
```

> Revise a documentação do [OpenTelemetry Operator](https://opentelemetry.io/docs/k8s-operator/)

## Criando um APM Domain

1. Abra o OCI e no menu hamburger navegue para **Observability and Management -> Application Performance Monitoring -> Administration**

![Printscreen da tela de navegação do OCI](/images/APM-Admin.png)

2. Clique no botão **Create APM Domain**
- De um nome ao domínio
- Selecione o compartimento
- (Opcional) Adicione um comentário
- (Opcional) Crie o Domínio no Free Tier da sua tenancy

![Printscreen do formulário de criação do APM Domain](/images/createapmdomain.png)

## Obtendo as informações necessárias do APM Domain

Para o Colletor do OpenTelemetry enviar mensagem para os APM, precisamos de 2 informações Data Upload Endpoint e das Data Keys.

### Data Upload Endpoint

O Data Upload Endpoint vai ser o endpoint que vai receber as informações vindas do Colletor do OTEL. Ele fica no quadro informações gerais no APM Domain.

![Printscreen do Data Upload Endpoint](/images/datauploadendpoint.png)

> Salve a informação em algum local que consiga retornar com facilidade.

### Data Keys

No menu inferior do lado esquerdo da console do APM Domain podemos encontrar a Opção Data Keys. Vamos copiar as informações do Private Data Key.

![PrintScreen Data Keys](/images/datakeys.png)

> Salve a informação em algum local que consiga retornar com facilidade.

> Na [documentação](https://docs.oracle.com/en-us/iaas/application-performance-monitoring/doc/obtain-data-upload-endpoint-and-data-keys.html) você pode ler mais sobre a diferença entre a Data Key privada e a pública.

## Criando um OpenTelemetry Collector

Execute o código abaixo alterando as informações de **{DATA_KEY}** e **{DATA_UPLOAD_ENDPOINT}**.

```kubectl
cat <<EOF | kubectl apply -f -
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: simplest
spec:
  config: |
    receivers:
      otlp:
        protocols:
          grpc:
          http:
    exporters:
      otlphttp:
        endpoint: "{DATA_UPLOAD_ENDPOINT}/20200101/opentelemetry/private"
        headers:
          Authorization: "dataKey {DATA_KEY}"
      otlphttp/metrics:
        endpoint: "{DATA_UPLOAD_ENDPOINT/20200101/opentelemetry"
        headers:
          Authorization: "dataKey {DATA_KEY}"
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: []
          exporters: [otlphttp]
        metrics:
          receivers: [otlp]
          processors: []
          exporters: [otlphttp/metrics]
EOF
```

Confira se o pod do collector já está no rodando

```bash
kubectl get pods | grep simplest-collector
simplest-collector-64cfc4d8d7-cwkv7           1/1     Running   0          30s
```

## Testando a configuração

Vamos executar 3 testes: 

1. Será criado um webserver Python com Flask que contêm as libs do OpenTelemetry configurado para enviar os traces para o collector criado anteriormente.

2. Será testada a funcionalidade do OpenTelemetry Injecting Auto-instrumentation, que irá realizar as configurações necessárias, em um webserver Python com Flask sem as libs do OpenTelemetry. Para que o pod envie os traces para o collector.

3. Será feita a alteração do Deployment anterior para em vez de enviar as informações para um Collector central, ele irá enviar para um collector configurado como sidecar.

### Primeiro Teste

Execute o comando abaixo: 

> Se o Colletor foi criado com o nome diferente do comando anterior ou em um namespace diferente, atualize a variável COLLECTOR-ENDPOINT no deployment. 

```bash
cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: flask-app
  template:
    metadata:
      labels:
        app: flask-app
    spec:
      containers:
        - name: flask-app
          image: pedrochristo/teste-python-otel-lib:latest
          ports:
            - containerPort: 5000
          env:
          - name: COLLECTOR-ENDPOINT
            value: "http://simplest-collector.default:4317"
---
apiVersion: v1
kind: Service
metadata:
  name: flask-service
  annotations:
spec:
  type: LoadBalancer
  ports:
    - name: http
      port: 80
      targetPort: 5000
  selector:
    app: flask-app
EOF
```

O código da aplicação e o dockerfile podem ser encontrardos [aqui](/python-opentelemetry-lib/).

Utilize o comando abaixo para conseguir o ip do service do deploy.

```bash
kubectl get svc flask-service
NAME            TYPE           CLUSTER-IP     EXTERNAL-IP      PORT(S)        AGE
flask-service   LoadBalancer   10.96.59.226   xx.xx.xx.xx      80:30728/TCP   58s
```
Abra o navegador e execute uma chamada no seguinte URL

http://{EXTERNAL-IP}:80/hello

Abra o trace explorer do APM na console do OCI, a partir do menu de hamburguer navegue **Observability and Management > Application Performance Monitoring > Trace Explorer**

![Printscreen Navegação Trace Explorer](/images/traceexplorer.png)

Filtre pelo compartment e pelo APM Domain na parte superior a direita e você deve ver alguns traces como os abaixo.

![Printscreen trace python com otel lib](/images/trace-python-otel-lib.png)
