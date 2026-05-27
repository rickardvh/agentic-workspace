const payload = {
  command: process.argv[2],
  args: process.argv.slice(2),
};
console.log(JSON.stringify(payload));
