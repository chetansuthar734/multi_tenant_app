function MessageReducer(state={messages:[]} , action){
switch(action.type){
    case "addMessages": return {...state,messages:[...state.messages,...action.payload]}
    case "removeMessages": return {...state,messages: [],};

    default :
    return state
}
}
function FileReducer(state={files:[]} , action){
switch(action.type){
    case "addfile": return {...state,files:[...state.files,...action.payload]}
    case "removefile": return {...state,files:state.files.filter((f,i)=>f.file_id !==action.payload) }
    case "remove_all_files": return {...state,files:[]}
    default :
    return state
}
}

export { MessageReducer ,FileReducer}