import {CaseDetail} from '../../../../components/pages'; export default async function Page({params}){const {id}=await params; return <CaseDetail id={id}/>;}
