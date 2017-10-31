# docker run -it -v corpus:/python-fuzz/corpus cpython
FROM ubuntu:xenial

RUN apt-get update
RUN apt-get install -y git

RUN git clone https://github.com/python/cpython.git

RUN apt-get install -y build-essential zlib1g-dev

WORKDIR /cpython

RUN ./configure

RUN apt-get install -y libffi-dev libssl-dev openssl

RUN make -j8
RUN make install

RUN python3 -m ensurepip
RUN python3 -m pip install coverage

WORKDIR /python-fuzz
COPY *.py /python-fuzz/

CMD python3 fuzzer.py
