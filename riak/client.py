"""
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""
# Use json as first choice, simplejson as second choice.
try:
    import json
except ImportError:
    import simplejson as json

from riak.bucket import RiakBucket
from riak.mapreduce import RiakMapReduce
from riak.search import RiakSearch
from riak.transports import RiakHttpTransport
from riak.util import deprecated
from riak.util import deprecateQuorumAccessors


@deprecateQuorumAccessors
class RiakClient(object):
    """
    The ``RiakClient`` object holds information necessary to connect to
    Riak. The Riak API uses HTTP, so there is no persistent
    connection, and the ``RiakClient`` object is extremely lightweight.
    """
    def __init__(self, host='127.0.0.1', port=8098, prefix='riak',
                 mapred_prefix='mapred', transport_class=None,
                 client_id=None, solr_transport_class=None,
                 transport_options=None):
        """
        Construct a new ``RiakClient`` object.

        :param host: Hostname or IP address
        :type host: string
        :param port: Port number
        :type port: integer
        :param prefix: Interface prefix
        :type prefix: string
        :param mapred_prefix: MapReduce prefix
        :type mapred_prefix: string
        :param transport_class: transport class to use
        :type transport_class: :class:`RiakTransport`

        :param solr_transport_class: HTTP-based transport class for
                                     Solr interface queries
        :type solr_transport_class: :class:`RiakHttpTransport`
        :param transport_options: Optional key-value args to pass to
                                  the transport constuctor
        :type transport_options: dict
        """
        if transport_class is None:
            transport_class = RiakHttpTransport

        api = getattr(transport_class, 'api', 1)
        if api >= 2:
            hostports = [(host, port), ]
            self._cm = transport_class.default_cm(hostports)

            # If no transport options are provided, then default to the
            # empty dict, otherwise just pass through what we are provided.
            if transport_options is None:
                transport_options = {}

            self._transport = transport_class(self._cm,
                                              prefix=prefix,
                                              mapred_prefix=mapred_prefix,
                                              client_id=client_id,
                                              **transport_options)
        else:
            deprecated('please upgrade the transport to the new API')
            self._cm = None
            self._transport = transport_class(host, port, client_id=client_id)

        self._encoders = {'application/json': json.dumps,
                          'text/json': json.dumps}
        self._decoders = {'application/json': json.loads,
                          'text/json': json.loads}
        self._solr = None
        self._host = host
        self._port = port

    def __hash__(self):
        return hash(frozenset(self._cm.hostports))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def __nq__(self, other):
        if isinstance(other, self.__class__):
            return hash(self) != hash(other)
        else:
            return True

    def get_transport(self):
        """
        Get the transport instance the client is using for it's connection.
        """
        return self._transport

    def get_client_id(self):
        """
        Get the ``client_id`` for this ``RiakClient`` instance.

        :rtype: string
        """
        return self._transport.get_client_id()

    def set_client_id(self, client_id):
        """
        Set the client_id for this ``RiakClient`` instance.

        .. warning::

           Refer to
           http://wiki.basho.com/Client-Implementation-Guide.html#Client-IDs
           for information on how to set the client_id.

        :param client_id: The new client_id.
        :type client_id: string
        :rtype: self
        """
        self._transport.set_client_id(client_id)
        return self

    def get_encoder(self, content_type):
        """
        Get the encoding function for the provided content type.
        """
        if content_type in self._encoders:
            return self._encoders[content_type]

    def set_encoder(self, content_type, encoder):
        """
        Set the encoding function for the provided content type.

        :param encoder:
        :type encoder: function
        """
        self._encoders[content_type] = encoder
        return self

    def get_decoder(self, content_type):
        """
        Get the decoding function for the provided content type.
        """
        if content_type in self._decoders:
            return self._decoders[content_type]

    def set_decoder(self, content_type, decoder):
        """
        Set the decoding function for the provided content type.

        :param decoder:
        :type decoder: function
        """
        self._decoders[content_type] = decoder
        return self

    def get_buckets(self):
        """
        Get the list of buckets.
        NOTE: Do not use this in production, as it requires traversing through
        all keys stored in a cluster.
        """
        return self._transport.get_buckets()

    def bucket(self, name):
        """
        Get the bucket by the specified name. Since buckets always exist,
        this will always return a :class:`RiakBucket <riak.bucket.RiakBucket>`.

        :rtype: :class:`RiakBucket <riak.bucket.RiakBucket>`
        """
        return RiakBucket(self, name)

    def is_alive(self):
        """
        Check if the Riak server for this ``RiakClient`` instance is alive.

        :rtype: boolean
        """
        return self._transport.ping()

    def add(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.add`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return apply(mr.add, args)

    def search(self, *args):
        """
        Start assembling a Map/Reduce operation based on search
        results. This command will return an error unless executed
        against a Riak Search cluster. A shortcut for
        :func:`RiakMapReduce.search`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return apply(mr.search, args)

    def index(self, *args):
        """
        Start assembling a Map/Reduce operation based on secondary
        index query results.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return apply(mr.index, args)

    def link(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.link`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return apply(mr.link, args)

    def map(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.map`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return apply(mr.map, args)

    def reduce(self, *args):
        """
        Start assembling a Map/Reduce operation. A shortcut for
        :func:`RiakMapReduce.reduce`.

        :rtype: :class:`RiakMapReduce`
        """
        mr = RiakMapReduce(self)
        return apply(mr.reduce, args)

    def get_index(self, bucket, index, startkey, endkey=None):
        return self._transport.get_index(bucket, index, startkey, endkey)

    def solr(self):
        if self._solr is None:
            self._solr = RiakSearch(self, host=self._host, port=self._port)

        return self._solr
