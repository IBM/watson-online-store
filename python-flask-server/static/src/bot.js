/**
 * This file contains all of the web and hybrid functions for interacting with 
 * the basic chat bot output.
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

    var chat = document.getElementById('chatBox');
    var bubble = document.createElement('div');
    bubble.className = 'message';  // Wrap the text first in a message class for common formatting

    // Set chat bubble color and position based on the user parameter
	if (user === watson) {
        bubble.innerHTML = "<div class='bot'>" + text + "</div>";
    } else {
        bubble.innerHTML = "<div class='user'>" + text + "</div>";
    }

    chat.appendChild(bubble);
    chat.scrollTop = chat.scrollHeight;  // Move chat down to the last message displayed

    return null;
}