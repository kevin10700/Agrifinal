/** Catálogo maestro Agrivale: ejecutar con el adaptador de BD del despliegue. */
const grupos = {
  FERTILIZANTES_QUIMICOS: ['Urea 46%','Sulfato de Amonio','Nitrato de Amonio','Nitrato de Calcio','Nitrato de Potasio','Fosfato Diamónico DAP','Fosfato Monoamónico MAP','Triple 17','Triple 16','Triple 15','Cloruro de Potasio','Sulfato de Potasio','Superfosfato Triple','Superfosfato Simple','Mezcla Física 12-24-12','Mezcla Física 20-20-0','Mezcla Física 18-46-0','Micronutrientes Quelatados','Sulfato de Zinc','Sulfato de Magnesio'],
  ABONOS_ORGANICOS: ['Composta Orgánica','Lombricomposta','Estiércol Bovino Compostado','Estiércol de Gallina','Bokashi','Humus de Lombriz','Guano de Murciélago','Harina de Hueso','Harina de Sangre','Harina de Pescado','Té de Composta','Extracto de Algas Marinas','Ácidos Húmicos','Ácidos Fúlvicos','Biofertilizante Líquido'],
  AGROQUIMICOS: ['Glifosato','Paraquat','2,4-D Amina','Atrazina','Metsulfurón Metil','Imidacloprid','Clorpirifos','Lambda Cihalotrina','Cipermetrina','Abamectina','Spinosad','Mancozeb','Oxicloruro de Cobre','Azoxistrobin','Tebuconazol','Metalaxil','Propiconazol','Carbendazim','Bacillus thuringiensis','Jabón Potásico','Aceite de Neem','Trampas Cromáticas','Adherente Agrícola','Regulador de Crecimiento','Coadyuvante Siliconado'],
  BOMBAS_RIEGO: ['Bomba Centrífuga 1 HP','Bomba Centrífuga 2 HP','Bomba Sumergible 1 HP','Motobomba Gasolina 2 Pulgadas','Motobomba Gasolina 3 Pulgadas','Aspersor de Impacto','Microaspersor','Cinta de Riego 16 mm','Manguera de Riego 1 Pulgada','Filtro de Disco','Filtro de Arena','Válvula de Bola','Válvula Reguladora de Presión','Programador de Riego','Conector para Cinta'],
  HERRAMIENTAS_PLASTICOS: ['Pala Cuadrada','Pala Redonda','Azadón','Machete','Tijera de Poda','Carretilla','Rastrillo','Guantes de Trabajo','Botas de Hule','Aspersora Manual 20 L','Aspersora de Mochila Motorizada','Malla Sombra 50%','Malla Antigranizo','Plástico Acolchado','Plástico para Invernadero','Charola de Germinación','Maceta de Vivero','Rafia Agrícola','Tutor de Bambú','Cuchillo de Cosecha']
};

const presentaciones = {
  FERTILIZANTES_QUIMICOS: ['1kg', '5kg', '25kg', '50kg'],
  ABONOS_ORGANICOS: ['1kg', '5kg', '25kg', '50kg'],
  AGROQUIMICOS: ['250ml', '1L', '5L'],
  BOMBAS_RIEGO: ['unidad'],
  HERRAMIENTAS_PLASTICOS: ['unidad']
};

const uso = {
  FERTILIZANTES_QUIMICOS: 'Nutrición mineral para el cultivo.',
  ABONOS_ORGANICOS: 'Mejora de suelo y nutrición orgánica.',
  AGROQUIMICOS: 'Manejo agrícola conforme a etiqueta y recomendación técnica.',
  BOMBAS_RIEGO: 'Riego y conducción de agua para cultivo.',
  HERRAMIENTAS_PLASTICOS: 'Labores de siembra, protección y cosecha.'
};

let id = 1;
const productos = Object.entries(grupos).flatMap(([categoria, nombres]) => nombres.map((nombre) => ({
  id: id++, nombre, categoria,
  uso_principal: nombre === 'Urea 46%' ? 'Fuente de nitrógeno para crecimiento vegetativo' : uso[categoria],
  presentaciones: presentaciones[categoria], precio_base: 0, stock: 0, imagen_url: '', activo: true
})));

if (productos.length !== 95) throw new Error('El catálogo maestro debe contener exactamente 95 productos.');
module.exports = productos;
