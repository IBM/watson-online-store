
/**
 * Copyright 2015 IBM Corp. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// The Api module is designed to handle all interactions with the server

var socket = null;
var Api = (function() {
  var requestPayload;
  var responsePayload;
   
  // Publicly accessible methods defined
  return {    
    sendRequestUsingSocket: sendRequestUsingSocket,

    // The request/response getters/setters are defined here to prevent internal methods
    // from calling the methods without any of the callbacks that are added elsewhere.
    getRequestPayload: function() {
      return requestPayload;
    },
    setRequestPayload: function(newPayloadStr) {
      requestPayload = newPayloadStr;
    },
    getResponsePayload: function() {
      return responsePayload;
    },
    setResponsePayload: function(newPayloadStr) {
      responsePayload = newPayloadStr;
    }
  };

  // Send a message request to the server
  function sendRequestUsingSocket(text, context) {
    // Build request payload
    var payloadToWatson = {};
    if (text) {
      payloadToWatson.data = text;
    }
    if (context) {
      payloadToWatson.context = context;
    }


    // if only not connected connect
    if(!socket || !socket.connected){
      // Namespace here needs to match the one used in server.py
      var namespace = '/wos';
      // Connect via Flask SocketIO
      socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + namespace); 

      socket.on('my_response', function(msg) {
        console.log(msg);     
        Api.setResponsePayload(msg);      
      });

    }

    socket.emit('my_event', payloadToWatson);  
    Api.setRequestPayload(payloadToWatson);                    
  }
}());
