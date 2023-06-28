# Enviando dados apra o OCI APM através OpenTelemetry Collector

![Baner OCI OTEL](/images/apmociotel.png)

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
    - [Segundo Teste](#segundo-teste)
    - [Terceiro Teste](#terceiro-teste)



## Instalando o Operator

### Pré-requisitos

Para a instalação do Operador do OpenTelemetry para Kubernetes, é preciso ter o Cert-Manager instalado.

> Veja a documentação do [**Cert-Manager**](https://cert-manager.io/docs/installation/) 

Pode ser instalado através do comando baixo:

```bash 
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.11.0/cert-manager.yaml 
```
 Se tiver um **OKE** (Oracle Kubernetes Engine) Ehenced Cluster no OCI é possível adicionar através dos Add-ons. Documentação [aqui](https://docs.oracle.com/en-us/iaas/Content/ContEng/Tasks/contengconfiguringclusteraddons.htm#contengconfiguringclusteraddons).

### Instalação

Para instalar o Operator para Kubernetes basta executar o comando abaixo:

```bash
kubectl apply -f https://github.com/open-telemetry/opentelemetry-operator/releases/latest/download/opentelemetry-operator.yaml
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

```bash
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
        endpoint: "{DATA_UPLOAD_ENDPOINT}/20200101/opentelemetry"
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

### Segundo Teste

OpenTelemetry tem um injector de Auto-instrumentation para as linguagens: .NET, Python, nodeJS e Java. Isso quer dizer que é possível adaptar um código que não tem as libs do OpenTelemetry, o Operator fará uma injeção das ferramentas necessárias para monitorar a aplicação.

1. Primeiro é preciso criar o *instrumentation* para a linguagem desejada. Aqui o será criada a *instrumentation* para Python, mas na [documentação](https://opentelemetry.io/docs/k8s-operator/automatic/) pode ser encontrada a configuração para as outras linguagens.

Execute o comando abaixo.

```bash
cat <<EOF | kubectl apply -f -
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: python
spec:
  exporter:
    endpoint: http://simplest-collector.default:4318
  propagators:
    - jaeger
    - b3
  sampler:
    type: parentbased_traceidratio
    argument: "1"
EOF
```

> Se for tiver sido feita alguma alteração no deployement do Collector, é preciso atualizar o campo do **endpoint**.

2. Com o *instrumentation* criado, é preciso atualizar o deployment python criado anteriormente para utilizar uma docker image onde o código de python não tem as libs do opentelemetry. Vamos utilizar o seguinte [código](/python-sem-opentelemetry/).

Execute o comando abaixo.

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
      annotations:
        instrumentation.opentelemetry.io/inject-python: 'true'
    spec:
      containers:
        - name: flask-app
          image: pedrochristo/teste-python-otel-semlib:latest
          ports:
            - containerPort: 5000
EOF
```

Após a atualização do deployment repita o processo de realizar algumas chamadas no ip público do service e depois validar se os traces apareceram no Trace Explorer do APM.

### Terceiro Teste

OpenTelemetry Operator oferece também a possibilidade de executar o collector como um sidecar de cada pod.

Para isso será alterada a confiração do Colletor para a de sidecar, e será adicionada uma annotation no deployment para ocorrer a injeção do sidecar no pod, além do endpoint do OpenTelemetry que em vez de apontar para o service do collector vai apontar para o localhost.

> Para mais informações sobre usar o Colletor como sidecar visite a [documentação](https://github.com/open-telemetry/opentelemetry-operator).

1. Alteração da Configuração do Collector

Execute o código abaixo alterando as informações de **{DATA_KEY}** e **{DATA_UPLOAD_ENDPOINT}**.

```bash
cat <<EOF | kubectl apply -f -
apiVersion: opentelemetry.io/v1alpha1
kind: OpenTelemetryCollector
metadata:
  name: simplest
spec:
  mode:sidecar
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
        endpoint: "{DATA_UPLOAD_ENDPOINT}/20200101/opentelemetry"
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

2. Fazer alteração do Instrumentation para apontar para o localhost.

```bash
cat <<EOF | kubectl apply -f -
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: python
spec:
  exporter:
    endpoint: http://localhost:4318
  propagators:
    - jaeger
    - b3
  sampler:
    type: parentbased_traceidratio
    argument: "1"
EOF
```

3. Alterar o Deployment para adicionar a annotation do sidecar Collector e já subir novamente com a nova configuração do instrumentation.

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
      annotations:
        sidecar.opentelemetry.io/inject: 'true'
        instrumentation.opentelemetry.io/inject-python: 'true'
    spec:
      containers:
        - name: flask-app
          image: pedrochristo/teste-python-otel-semlib:latest
          ports:
            - containerPort: 5000
EOF
```

Após a atualização do deployment repita o processo de realizar algumas chamadas no ip público do service e depois validar se os traces apareceram no Trace Explorer do APM.