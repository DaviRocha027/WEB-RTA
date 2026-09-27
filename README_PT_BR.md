# WEB-RTA — Write-up de Segurança de Aplicações Web

> **Segurança de Aplicações Web | Pentest | Red Team | Análise de Vulnerabilidades**

Write-up documentando minha abordagem para resolução de um desafio do **WEB-RTA**, incluindo reconhecimento, enumeração, identificação de vulnerabilidades, exploração e encadeamento de ataques.

O objetivo deste documento não é apenas registrar as vulnerabilidades encontradas, mas também demonstrar o **raciocínio e a metodologia utilizados durante a avaliação**.

---

## ⚠️ Aviso

Este repositório foi criado para **fins educacionais e de portfólio**.

Todos os testes descritos foram realizados em um ambiente de treinamento autorizado.

Credenciais, tokens de sessão, cookies e outras informações sensíveis foram removidos ou mascarados da versão pública.

---

# Sumário

* [Visão Geral](#visão-geral)
* [Metodologia](#metodologia)
* [Cadeia de Ataque](#cadeia-de-ataque)
* [1. Análise do JWT](#1-análise-do-jwt)
* [2. Enumeração de Endpoints](#2-enumeração-de-endpoints)
* [3. SQL Injection](#3-sql-injection)
* [4. XXE](#4-xxe)
* [5. SSRF](#5-ssrf)
* [6. Decodificação das Informações](#6-decodificação-das-informações)
* [7. Segunda Aplicação](#7-segunda-aplicação)
* [8. Manipulação do Scope OAuth](#8-manipulação-do-scope-oauth)
* [9. Enumeração do OTP](#9-enumeração-do-otp)
* [10. Acesso Administrativo](#10-acesso-administrativo)
* [Vulnerabilidades Identificadas](#vulnerabilidades-identificadas)
* [Ferramentas Utilizadas](#ferramentas-utilizadas)
* [Principais Aprendizados](#principais-aprendizados)

---

# Visão Geral

O desafio envolveu duas aplicações web interligadas.

A aplicação inicial apresentava diversas vulnerabilidades que poderiam ser encadeadas para obter acesso a um serviço interno e recuperar informações necessárias para acessar uma segunda aplicação.

A cadeia de exploração envolveu:

* Manipulação de JWT
* Falhas de autorização
* SQL Injection
* XXE
* SSRF
* Acesso a serviço interno
* Decodificação de informações
* Manipulação de escopo OAuth
* OTP fraco
* Brute-force de OTP

A cadeia geral de exploração foi:

```text
Análise do JWT
     │
     ▼
Manipulação da Role
     │
     ▼
Identificação de Usuário
     │
     ▼
SQL Injection
     │
     ▼
Bypass de Autenticação
     │
     ▼
Acesso Administrativo
     │
     ├───────────────┐
     ▼               ▼
    XXE             SSRF
                      │
                      ▼
             Serviço Interno
                      │
                      ▼
              Dados Codificados
                      │
                      ▼
                  Credenciais
                      │
                      ▼
             Segunda Aplicação
                      │
                      ▼
            Abuso do OAuth Scope
                      │
                      ▼
                  Validação OTP
                      │
                      ▼
               Enumeração OTP
                      │
                      ▼
            Acesso Administrativo
                      │
                      ▼
                Última Flag
```

---

# Metodologia

Durante o desafio, procurei seguir uma abordagem estruturada:

```text
Reconhecimento
      ↓
Enumeração
      ↓
Identificação da superfície de ataque
      ↓
Formulação de hipótese
      ↓
Validação da hipótese
      ↓
Exploração
      ↓
Análise do resultado
      ↓
Utilização das informações obtidas
      ↓
Continuidade da exploração
```

Um dos principais objetivos foi não tratar cada vulnerabilidade como um achado isolado.

As informações obtidas em uma etapa foram utilizadas para orientar os testes seguintes.

---

# 1. Análise do JWT

Iniciei a avaliação interceptando o tráfego da aplicação utilizando o **Burp Suite**.

Durante a análise inicial, identifiquei um **JSON Web Token (JWT)** utilizado pela aplicação.

Após decodificar o token utilizando o JWT.io, observei:

```text
alg: none
```

O payload também apresentava:

```text
role: anonymous
```

A possibilidade de modificar essas informações chamou minha atenção para o mecanismo de autorização da aplicação.

### Hipótese

A aplicação poderia estar confiando em informações controladas pelo cliente para tomar decisões relacionadas à autorização.

A partir disso, comecei a testar se a alteração do parâmetro `role` modificaria o comportamento da aplicação.

---

# 2. Enumeração de Endpoints

Realizei uma enumeração de endpoints e identifiquei:

```text
/login
/logout/
/dashboard
/admin/events
```

Um comportamento interessante foi observado ao acessar:

```text
/dashboard
```

sem realizar autenticação.

A aplicação retornava uma página que aparentava pertencer a uma área autenticada.

Em seguida, comecei a testar diferentes valores para a `role` presente no JWT.

Alterações para:

```text
administrator
```

e:

```text
admin
```

não apresentaram o resultado esperado.

Entretanto, ao utilizar:

```text
role=user
```

a aplicação retornou informações relacionadas a eventos.

Um dos eventos retornados continha:

```text
Masquerade Ball,user

Super Fun Event

Happening at: 2051-12-31 10:00

Created by: notatypicalsysadmin
```

Essa informação revelou um possível usuário válido:

```text
notatypicalsysadmin
```

Esse dado foi utilizado para orientar a próxima etapa da análise.

---

# 3. SQL Injection

Com o nome de usuário identificado, passei a analisar:

```text
/login
```

Com base no comportamento observado, levantei a hipótese de que o mecanismo de autenticação poderia ser vulnerável a **SQL Injection**.

Após testar diferentes payloads, o seguinte payload permitiu contornar a autenticação:

```text
notatypicalsysadmin' or 1=1--
```

Após o bypass, obtive acesso à aplicação e às funcionalidades administrativas.

Entre os endpoints disponíveis estavam:

```text
/admin/events
/fetch_internal_secret
```

### Vulnerabilidade identificada

**SQL Injection — Bypass de Autenticação**

A funcionalidade de login permitia a manipulação da consulta SQL utilizada durante o processo de autenticação.

---

# 4. XXE

Com acesso administrativo, continuei analisando a funcionalidade:

```text
/admin/events
```

Durante os testes, identifiquei:

```text
/admin/events/update/1
```

A requisição utilizava XML para atualizar as informações do evento.

Como o processamento de XML pode ser vulnerável ao uso indevido de entidades externas, testei a possibilidade de **XML External Entity (XXE)**.

Utilizei:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY conteudo SYSTEM "file:///etc/passwd">
]>
<event>
  <title>&conteudo;</title>
  <description>Super Fun Event</description>
  <happening_at>2051-12-31 10:00</happening_at>
  <visibility>user</visibility>
</event>
```

O objetivo era verificar se o parser XML permitiria a resolução de uma entidade externa apontando para um arquivo local.

O arquivo utilizado durante o teste foi:

```text
/etc/passwd
```

### Vulnerabilidade identificada

**XML External Entity (XXE)**

A aplicação permitia o processamento de entidades externas no XML fornecido pelo usuário, criando a possibilidade de acesso a recursos locais.

---

# 5. SSRF

Em seguida, analisei o endpoint:

```text
/fetch_internal_secret
```

principalmente sua funcionalidade relacionada à consulta de status.

O comportamento da aplicação indicava que ela realizava uma requisição HTTP com base em uma entrada fornecida pelo usuário.

Isso levantou a hipótese de **Server-Side Request Forgery (SSRF)**.

Para validar a hipótese, utilizei um endereço de loopback codificado:

```text
http%3A%2F%2F127%2E0%2E0%2E1%253A8000
```

A aplicação processou a requisição e retornou:

```text
requested_uri:
http://127.0.0.1:8000/secret
```

A resposta também indicava:

```text
status: success
status_code: 200
```

O campo `requested_uri` foi especialmente importante, pois confirmou que a requisição havia sido realizada pelo próprio servidor.

### Vulnerabilidade identificada

**Server-Side Request Forgery (SSRF)**

A aplicação permitia que uma entrada controlada pelo usuário influenciasse uma requisição HTTP realizada pelo servidor, permitindo acessar um serviço interno.

---

# 6. Decodificação das Informações

O serviço interno retornou uma informação armazenada no campo:

```text
hidden_in_layers
```

O conteúdo estava representado como valores hexadecimais:

```text
64 58 4e 6c 63 6c 38 30 5a 6d 49 33 4f 44 51 35 ...
```

Pelo formato, identifiquei que os valores representavam dados codificados em hexadecimal.

Após realizar a conversão, obtive uma nova string codificada.

A informação passou então por uma segunda etapa de decodificação, revelando as credenciais necessárias para acessar a segunda aplicação.

Por questões de segurança, as credenciais obtidas durante o desafio não são publicadas neste repositório.

### Processo

```text
Hexadecimal
    ↓
ASCII
    ↓
String codificada
    ↓
Decodificação
    ↓
Credenciais
```

---

# 7. Segunda Aplicação

Com as informações obtidas no serviço interno, passei para a análise da segunda aplicação.

Durante a enumeração, identifiquei:

```text
/client/login
```

Utilizando as credenciais obtidas na etapa anterior, consegui realizar a autenticação.

A aplicação identificou o cliente como:

```text
client_1337
```

Entretanto, o cliente possuía inicialmente apenas um escopo de leitura.

Isso indicou que o mecanismo de autorização seria uma área importante para investigação.

---

# 8. Manipulação do Scope OAuth

Continuei analisando as requisições utilizando o **Burp Suite**.

Durante a análise, identifiquei o parâmetro responsável pelo escopo de autorização.

O valor original era:

```text
read
```

Realizei um teste alterando para:

```text
admin
```

A aplicação aceitou a alteração e redirecionou o fluxo para:

```text
/oauth/otp
```

Esse comportamento indicou que a aplicação não estava validando adequadamente se o cliente possuía autorização para solicitar o escopo administrativo.

### Vulnerabilidade identificada

**Falha de Autorização / Manipulação de OAuth Scope**

Um cliente originalmente limitado ao escopo de leitura conseguiu solicitar um escopo administrativo através da alteração de um parâmetro controlado pelo cliente.

---

# 9. Enumeração do OTP

Após a alteração do escopo, a aplicação solicitou um OTP de três dígitos.

O espaço de busca era:

```text
000 - 999
```

Totalizando apenas:

```text
1.000 combinações
```

Automatizei as tentativas utilizando um script em Python.

Também seria possível utilizar o **Burp Suite Intruder** para realizar o mesmo processo utilizando uma lista numérica.

A aplicação não apresentava proteção suficiente contra tentativas repetidas, permitindo testar sistematicamente as possibilidades.

Após identificar o OTP válido, consegui avançar no processo de autenticação.

### Vulnerabilidade identificada

**OTP fraco / Ausência de proteção contra brute-force**

A utilização de apenas três dígitos, combinada com a ausência de mecanismos suficientes contra tentativas repetidas, reduziu significativamente a segurança da autenticação.

---

# 10. Acesso Administrativo

Após identificar o OTP válido, concluí o fluxo de autenticação.

A aplicação concedeu acesso administrativo.

Com esse nível de acesso, consegui consultar informações adicionais do sistema e concluir a etapa final do desafio.

Durante essa etapa, encontrei a **última flag**, encerrando a resolução do WEB-RTA.

---

# Vulnerabilidades Identificadas

| #  | Vulnerabilidade                         | Impacto                                       |
| -- | --------------------------------------- | --------------------------------------------- |
| 01 | JWT `alg: none`                         | Manipulação do token / falha de autorização   |
| 02 | Falha de autorização                    | Role controlada pelo cliente afetava o acesso |
| 03 | SQL Injection                           | Bypass de autenticação                        |
| 04 | XXE                                     | Possível acesso a recursos/arquivos locais    |
| 05 | SSRF                                    | Acesso a serviços internos                    |
| 06 | Exposição de informações                | Serviço interno retornando dados sensíveis    |
| 07 | Manipulação de OAuth Scope              | Possível escalada de privilégios              |
| 08 | OTP fraco                               | Redução da segurança da autenticação          |
| 09 | Ausência de proteção contra brute-force | Permitia enumeração do OTP                    |

---

# Cadeia de Ataque

O aspecto mais interessante do desafio foi o encadeamento das vulnerabilidades.

O problema inicial relacionado ao JWT forneceu informações que permitiram identificar um usuário.

O usuário identificado direcionou os testes para o mecanismo de autenticação, onde foi encontrada uma SQL Injection.

O bypass de autenticação permitiu acesso administrativo, abrindo novas funcionalidades para análise.

A partir desse acesso foram identificadas vulnerabilidades de XXE e SSRF.

O SSRF permitiu acessar um serviço interno que retornava informações codificadas.

Após a decodificação, foram obtidas as credenciais necessárias para acessar a segunda aplicação.

Na segunda aplicação, uma falha de autorização permitiu modificar o escopo de `read` para `admin`.

Por fim, a proteção inadequada do OTP permitiu a enumeração do código e a obtenção de acesso administrativo.

---

# Ferramentas Utilizadas

### Testes Web

* Burp Suite
* Burp Suite Intruder
* Browser Developer Tools

### Reconhecimento

* Ferramentas de fuzzing
* Enumeração de diretórios e endpoints

### Análise

* JWT.io
* Ferramentas de encoding/decoding
* Python

---

# Skills Demonstrated

Durante este desafio, pratiquei:

* Reconhecimento de aplicações web
* Enumeração de endpoints
* Análise de JWT
* Testes de autenticação
* SQL Injection
* Bypass de autenticação
* Exploração de XXE
* Exploração de SSRF
* Enumeração de serviços internos
* Análise de dados codificados
* Testes de autorização OAuth
* Escalada de privilégios
* Testes de OTP
* Brute-force controlado
* Análise de tráfego com Burp Suite
* Automação básica com Python
* Encadeamento de vulnerabilidades

---

# Principais Aprendizados

Este desafio reforçou um dos conceitos mais importantes durante um pentest:

> **Uma vulnerabilidade não precisa necessariamente fornecer acesso direto ao objetivo final. Ela pode fornecer uma informação que possibilita a próxima etapa da exploração.**

O aspecto mais valioso do desafio foi entender como diferentes vulnerabilidades poderiam ser combinadas para construir uma cadeia de ataque.

O processo seguido foi:

```text
Observar
   ↓
Entender
   ↓
Formular uma hipótese
   ↓
Testar
   ↓
Analisar o resultado
   ↓
Extrair informações úteis
   ↓
Atualizar o caminho de ataque
   ↓
Repetir
```

Essa abordagem permitiu transformar vulnerabilidades individuais em uma cadeia completa de exploração.

---

# Resultado Final

**WEB-RTA Challenge — Concluído ✅**

O desafio foi resolvido através do encadeamento de múltiplas vulnerabilidades em duas aplicações web, resultando em acesso administrativo e obtenção da última flag.

---

## Autor

**Davi Rocha**

Cybersecurity | Web Application Security | Pentest | Red Team

---

> Este write-up representa meu processo de aprendizado e documenta a metodologia utilizada durante a resolução do desafio.
