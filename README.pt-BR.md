# Corpus Font Bundle

**Versão de desenvolvimento 0.1.0.** Software original e aberto da [Lofrano Tecnologia](https://lofranotecnologia.com.br). [English](README.md).

Cria arquivos TTF/WOFF2 para um corpus Unicode explícito e compara a composição tipográfica com a fonte original usando o executável independente HarfBuzz. Mudanças em nomes de glifos, clusters, posições, avanços ou impressões digitais dos contornos impedem a publicação. A equivalência vale somente para os casos fornecidos, não para textos não testados nem para todos os renderizadores.

## Instalação

Ambiente suportado: Linux, CPython 3.13, `/usr/bin/hb-shape` 6.0.0 com compositor OT, fontTools 4.68.0 e Brotli 1.2.1. A [qualificação](docs/qualification.md) registra a origem exata da qualificação anterior ao código. Biblioteca, testes e demonstração não baixam dependências.

No Debian Bookworm, prepare explicitamente as dependências antes de trabalhar offline:

```sh
apt-get update
apt-get install --no-install-recommends libharfbuzz-bin=6.0.0+dfsg-3 libharfbuzz0b=6.0.0+dfsg-3
python -m venv .venv
. .venv/bin/activate
python -m pip install --only-binary=:all: --require-hashes -r requirements.lock
python -m pip install --only-binary=:all: --require-hashes -r requirements-build.lock
python -m pip install --no-build-isolation --no-deps .
```

A instalação de pacotes do sistema exige o administrador apropriado; não exige contêiner privilegiado. O arquivo de hashes cobre os artefatos de execução da plataforma qualificada, não as ferramentas de empacotamento.

## Testes e demonstração

```sh
python -m unittest discover -s tests
python -m corpus_font_bundle demo --assert
python -m corpus_font_bundle demo --assert --json
```

Os testes usam composição nativa real, decodificação WOFF2, candidatos adulterados, cancelamento de processos e instalação offline de wheel fora do diretório do projeto. Prepare `pip`, as ferramentas fixadas em `requirements-build.lock` antes dos testes. Não há simulação substituindo HarfBuzz nos testes de equivalência.

Exemplo de saída humana, mantida em inglês na CLI:

```text
Corpus Font Bundle — development 0.1.0
Glyphs: 9 -> 8; removed: Z
Replay: 5 cases matched original, TTF and decoded WOFF2
Advances: fi=550; f+i=600; Á=600; A+U+0301=600; AA=560+600
Missing Ω: MISSING_CHARACTER (count=1), no bundle
Repeat build: identical
Oracle: PASS
```

A opção `--json` também apresenta hashes calculados dos artefatos. A demonstração é determinística com a mesma cadeia de ferramentas e usa diretórios temporários. Todas as fontes de teste são sintéticas e originais.

## Exemplo de biblioteca

```python
from pathlib import Path
from corpus_font_bundle import buildBundle, verifyBundle, BundleError
from corpus_font_bundle.fixture import font_bytes, CORPUS, shaping_cases

source = Path('synthetic.ttf')
source.write_bytes(font_bytes())
try:
    result = buildBundle(source, CORPUS, shaping_cases(), {'destination': 'example-bundle'})
    verifyBundle(source, 'example-bundle')
    print(result['subset_glyph_count'])  # 8
except BundleError as error:
    print(error.as_dict())
```

O destino não pode existir, mesmo vazio. O sucesso retorna o manifesto completo; erros usam códigos estáveis e sanitizados. A fonte original é somente lida e conferida novamente antes da publicação.

Para a CLI, grave o corpus exato em UTF-8 em `corpus.txt` e uma lista de registros em `cases.json`:

```json
[{"text":"fi","language":"en","direction":"ltr","script":"Latn","features":{"liga":1,"kern":0}}]
```

```sh
corpus-font-bundle build --font synthetic.ttf --corpus-file corpus.txt --cases-file cases.json --destination font-bundle
corpus-font-bundle verify --font synthetic.ttf --bundle font-bundle
```

Sucesso: JSON em stdout. Erro da aplicação: JSON em stderr e código de saída 1. Erros de argumentos usam argparse e código 2. Diagnósticos da aplicação não expõem texto, caminhos de origem nem mensagens nativas.

## Decisões e limites

Cobertura Unicode não prova preservação de ligaturas ou posicionamento. FontTools fornece os leitores, o fechamento de substituições, o subconjunto e WOFF2. HarfBuzz fornece a composição real. Nomes post estáveis evitam comparar IDs renumerados; pens mantidos pela fontTools expandem componentes antes do hash. O diretório completo é publicado por renomeação sem sobrescrita somente após as verificações.

- Uma face TrueType estática, sem cor, com nomes post de formato 2. Sem coleções, CFF, fontes variáveis ou descoberta automática.
- Corpus até 16.384 pontos de código; 1–64 casos com soma de textos até 16.384 pontos. Idioma, escrita, direção e recursos explícitos. Não há normalização: `Á` e `A` + U+0301 continuam distintos.
- Fonte e cada artefato binário até 16 MiB; até 4.096 glifos após leitura. Decodificadores nativos podem alocar antes dessa inspeção. **Não é um sandbox de fontes.**
- Prazo monotônico de cinco segundos por filho nativo; saída combinada limitada a 256 KiB. Travamentos do sistema operacional não têm garantia de interrupção instantânea.
- Todo `fsType` diferente de zero é rejeitado. Zero não concede direitos de redistribuição. Registros de nomes e licenciamento são preservados. A licença MIT do programa não muda a licença das fontes do usuário.
- Sem pontuação visual, promessa de conformidade universal, telemetria, dependência de modelo/API ou alegação de implantação.

Veja o [contrato preciso](docs/contract.md), [projeto](docs/design.md), [segurança](SECURITY.md) e [contribuição](CONTRIBUTING.md). Repositório: [martinlofranodeoliveira/corpus-font-bundle](https://github.com/martinlofranodeoliveira/corpus-font-bundle). Contato geral pelo site oficial.

`PUBLISHED_IO_ERROR` indica falha de I/O após o rename: o pacote completo já está visível e pode ser conferido com `verifyBundle`. Falhas de validação anteriores à publicação não deixam pacote final.
