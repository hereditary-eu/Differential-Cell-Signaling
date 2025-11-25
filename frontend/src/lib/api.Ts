/// <reference types="vite/client" />

export async function getData(): Promise<any> {
    const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/api/data`);
    if (!res.ok) {
        throw new Error(`Failed to fetch data: ${res.status} ${res.statusText}`);
    }
    return res.json();
}

// import { GraphQLClient } from 'graphql-request';
//GraphQL is a declarative query language, cant be used for graph traversal
//Gremlin is traversal language for graphs

// const PUPPY_URL = import.meta.env.VITE_PUPPY_URL;
// const PUPPY_AUTH = import.meta.env.VITE_PUPPY_AUTH;

// export async function queryPuppyGraph(gremlinQuery) {
//     const url = import.meta.env.VITE_PUPPY_URL;
//     const auth = import.meta.env.VITE_PUPPY_AUTH;

//     const res = await fetch(url, {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'Authorization': 'Basic ' + btoa(`${auth}`)
//         },
//         body: JSON.stringify( { query: gremlinQuery } )
//     });

//     if (!res.ok) {
//         const text = await res.text();
//         throw new Error(`Puppygraph error: ${res.status} ${res.statusText} - ${text}`);
//     }

//     return res.json();
// }

// export const puppyGraphClient = new GraphQLClient(PUPPY_URL, {
//     headers: {
//         'Content-Type': 'application/json',
//         Authorization: `Basic ${btoa(PUPPY_AUTH)}`
//     }
// });

// // example query
// export async function getCellTypes() {
//     const query = `
//         query {
//             nodes(distinct_on: cellType) {
//                 cellType
//             }
//         }
//     `;
//     const data = await puppyGraphClient.request(query);
//     return data;
// }
