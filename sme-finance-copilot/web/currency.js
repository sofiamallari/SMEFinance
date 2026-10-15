/* Shared presentation only. No currency conversion or financial calculations. */
window.MerchantCurrency=(()=>{
 const meta=__CURRENCY_META__;
 const display=(value,currency,options)=>{if(value==null||value==='')return 'Unavailable';const number=Number(value);if(!Number.isFinite(number))return 'Unavailable';const prefix=currency===meta.code?meta.symbol:currency+' ';return (number<0?'-':'')+prefix+Math.abs(number).toLocaleString('en-US',options)};
 const format=(value,currency=meta.code)=>display(value,currency,{minimumFractionDigits:meta.decimals,maximumFractionDigits:meta.decimals});
 const compact=(value,currency=meta.code)=>display(value,currency,{notation:'compact',maximumFractionDigits:1});
 return Object.freeze({...meta,format,compact,label:currency=>currency===meta.code?meta.label:currency+' — Legacy / Manual Migration Required'});
})();
