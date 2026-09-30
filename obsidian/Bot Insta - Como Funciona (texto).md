---
tags: [bot-insta, leigo]
---

# bot-insta v2 - Como funciona (linguagem simples)

Espelho textual de [[Bot Insta - Como Funciona (mapa mental)]]. Versao tecnica: [[Bot Insta - Mapa Mental]].

## O que e

Uma IA que troca mensagens diretas no Instagram como se fosse uma pessoa de verdade. E um projeto pessoal. Ela escreve do jeito de uma pessoa real (com o nome trocado) e nao se apresenta como IA.

## Como ela aprende a falar

Pense em alguem que le uma conversa antiga para aprender como um amigo escreve:

- Le uma conversa real exportada do Instagram.
- Troca todos os nomes por nomes inventados.
- Mede o jeito de escrever: quanto escreve por mensagem, quantas mensagens seguidas manda, como ri, que girias usa, se esquece acentos e ponto final, quanto demora para responder.
- Guarda exemplos de "quando disseram isso, ela respondeu aquilo".

## Como ela responde

1. Espera voce parar de digitar.
2. Procura nos exemplos guardados algum momento parecido.
3. Pede a resposta para um modelo de IA, explicando quem ela e e como escreve.
4. Ajusta o texto para ficar com o jeito dela (tira ponto final, tira acento, quebra em mensagens curtas).
5. Manda uma mensagem por vez, com pausas de quem esta digitando.

Se um modelo de IA gratuito falhar ou estiver ocupado, ela tenta o proximo da lista sozinha, sem perder a conversa.

## O que ja funciona

- Uma janelinha de chat para testar.
- Um painel no navegador que entra na conta do Instagram (fica logado entre uma vez e outra), mostra as conversas, entende quando alguem responde uma mensagem especifica, quando manda reels, foto ou audio, e deixa mandar mensagens na mao.
- Uma persona de teste foi montada a partir de 467 mensagens reais (so o jeito de digitar: tamanho, risadas, pausas).
- A resposta automatica no Instagram nao existe: tudo que sai do painel e digitado por alguem.

## O que ainda falta

- Confirmar a permissao da pessoa que originou a persona. Ela tem 18 anos (adulta), entao a idade nao bloqueia; falta o consentimento e a decisao sobre quem sao os interlocutores.
- Gerar a biografia da persona (quem ela e, familia, gostos) sem dados que identifiquem a pessoa.

## Privacidade

- As conversas originais, os contatos, as chaves de acesso e o login salvo do Instagram ficam so no computador.
- Para a IA vai apenas o texto com os nomes trocados.
- A IA nao pode revelar como foi montada nem quais sao os nomes reais.
