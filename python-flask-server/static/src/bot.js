/**
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

/**
 * This file contains all of the web and hybrid functions for interacting with 
 * the basic chat bot output.
 * Leveraged from: https://github.com/sharpstef/watson-bot-starter
 */

"use strict";

var watson = 'Bot';


/**
 * @summary Display Chat Bubble.
 *
 * Formats the chat bubble element based on if the message is from the user or from Bot.
 *
 * @function displayMessage
 * @param {String} text - Text to be displayed in chat box.
 * @param {String} user - Denotes if the message is from Bot or the user. 
 * @return null
 */
function displayMessage(text, user) {

    if (text && text != "") {
        var chat = document.getElementById('chatBox');
        var bubble = document.createElement('div');

        // Set chat bubble color and position based on the user parameter
        if (user === watson) {
            bubble.className = 'bot_message';  // Bot text formatting
            bubble.innerHTML = "<div class='bot'>" + text + "</div>";
        } else {
            bubble.className = 'user_message';  // User text formatting
            bubble.innerHTML = "<div class='user'>" + text + "</div>";
        }

        chat.appendChild(bubble);
        chat.scrollTop = chat.scrollHeight;  // Move chat down to the last message displayed
    }

    return null;
}

function displayImage(url) {

    if (url) {
        var image = document.createElement("img");
        image.src = url;
        image.alt = url;
        image.className = 'thumbnail';  // Image formatting

        document.body.appendChild(image);

        var chat = document.getElementById('chatBox');
        chat.appendChild(image);
        chat.scrollTop = chat.scrollHeight;  // Move chat down to the last message displayed
    }

    return null;
}
