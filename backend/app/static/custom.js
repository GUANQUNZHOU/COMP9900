//1. show chat time
Date.prototype.timeNow = function(){ 
    return ((this.getHours() < 10)?"0":"") + ((this.getHours()>12)?(this.getHours()-12):this.getHours()) 
    +":"+ ((this.getMinutes() < 10)?"0":"") + this.getMinutes() 
    +":"+ ((this.getSeconds() < 10)?"0":"") + this.getSeconds() + ((this.getHours()>12)?('PM'):'AM'); };

var datetime = new Date().timeNow();
document.getElementById('time_out').innerHTML=datetime;
if (document.getElementById('time_rev')) {
    document.getElementById('time_rev').innerHTML=datetime;
}

//2. show/hide chatbot
$(document).ready(function(){
    var chat = document.getElementById("chat_container");
    console.log('ready')
    $(".chat_on").click(function(){
        console.log('clicked!')
        console.log(chat.style.display)
        if (chat.style.display == ""){
            console.log('show item')
            chat.style.display = 'block';
        }
    });
    
       $(".header-icons").click(function(){
        if (chat.style.display == "block"){
            console.log('close item')
            chat.style.display = '';
        }
           $(".chat_on").show(300);
    });
    
});
//3.upload PDF file
const upload_bt = document.getElementById('upload')
const upload_fl = document.querySelector('input[type="file"]')

upload_bt.addEventListener('click',function(){
    console.log('upload file');
    upload_fl.click();

});
upload_fl.addEventListener('change',function(e){
    console.log(upload_fl.files)
    console.log(upload_fl.files[0].name)
    const reader = new FileReader();
    const name = upload_fl.files[0].name;


    //after loading the file
    reader.onload = function(){
        console.log('onload')

        console.log(reader.result)
        var data = reader.result,
            base64 = data.replace(/^[^,]*,/, ''),
            info = {
                message: base64 //either leave this `basae64` or make it `data` if you want to leave the `data:application/pdf;base64,` at the start
            };
        $.post( "/send_file", {message: base64,fileName: name}, handle_response);
        var datetime = new Date().timeNow();
         // loading 
        console.log('put something...')
        $('.msg-page').append(`
            <div class="outgoing-chats" id="Analyzing">
                <div class="outgoing-msg-inbox">
                    <p>Analyzing........</p>
                    <span class="show-time" id="time_rev">
                        ${datetime}
                    </span>
                </div>
            </div>
          `)
      shouldScroll = chatWindow.scrollTop + chatWindow.clientHeight === chatWindow.scrollHeight;
        if (!shouldScroll) {
            scrollToBottom();
        }
        console.log('!!!!!!!scrolled up')
        console.log('HAHSAHHSDAHWHADHSQAWHdw...')
        // $( "#Analyzing" ).remove();
        function handle_response(data) {
          // append the bot repsonse to the div
          $('.msg-page').append(`
            <div class="outgoing-chats">
                <div class="outgoing-msg-inbox">
                    <p>${data.message}</p>
                    <span class="show-time" id="time_rev">
                        ${datetime}
                    </span>
                </div>
            </div>
          `)
          // remove the loading indicator
          $( "#Analyzing" ).remove();
          shouldScroll = chatWindow.scrollTop + chatWindow.clientHeight === chatWindow.scrollHeight;
            if (!shouldScroll) {
                scrollToBottom();
            }
            console.log('!!!!!!!scrolled up')
            
        }

    }
    // reader.readAsText(upload_fl.files[0])
    reader.readAsDataURL(upload_fl.files[0])
    console.log('huhihihi')
},false);

//4. show chat response and autoscroll
chatWindow = document.getElementById('chat-window'); 
function scrollToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

$('#target').on('submit', function(e){
        console.log('clicked submit')
        e.preventDefault();
        
        const input_message = $('#input_message').val();
        console.log(input_message)
        // return if the user does not enter any text
        if (!input_message) {
          return
        };
        var datetime = new Date().timeNow();

        $('.msg-page').append(`
            <div class="received-chats">
                <div class="received-msg">
                    <div class="received-msg-inbox">
                        <p>${input_message}</p>
                        <span class="show-time" id="time_rev">
                        ${datetime}
                        </span>
                    </div>
                </div>
            </div>
        `);

        // loading 
        $('.msg-page').append(`
            <div class="outgoing-chats" id="loading">
                <div class="outgoing-msg-inbox">
                    <p>Typing........</p>
                    <span class="show-time" id="time_rev">
                        ${datetime}
                    </span>
                </div>
            </div>
          `)

        // clear the text input 
        $('#input_message').val('');


        // send the message
        // submit_message(input_message);
        $.post( "/send_message", {message: input_message}, handle_response);
        
        var datetime = new Date().timeNow();
        function handle_response(data) {
          // append the bot repsonse to the div
          $('.msg-page').append(`
            <div class="outgoing-chats">
                <div class="outgoing-msg-inbox">
                    <p>${data.message}</p>
                    <span class="show-time" id="time_rev">
                        ${datetime}
                    </span>
                </div>
            </div>
          `)
          // remove the loading indicator
          $( "#loading" ).remove();
          shouldScroll = chatWindow.scrollTop + chatWindow.clientHeight === chatWindow.scrollHeight;
            if (!shouldScroll) {
                scrollToBottom();
            }
            console.log('!!!!!!!scrolled up')
            
        }
        scrollToBottom();

    });

function simuclick(){
    console.log('sim')
    ele = document.getElementById("logbook_open").click();
}


console.log('end')
scrollToBottom();



