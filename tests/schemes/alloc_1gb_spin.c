#include <stdio.h>
#include <stdlib.h>

int main(void)
{
	char *mem = malloc(1024 * 1024 * 1024);
	unsigned long i;

	for (i = 0; i < 1024 * 1024 * 1024; i += 4096)
		mem[i] = 1;

	while (1)
		;

	printf("hello\n");
	return 0;
}
